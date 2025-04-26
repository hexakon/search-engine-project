from flask import Flask, request, jsonify
from flask_cors import CORS
from elasticsearch import Elasticsearch, helpers
import pandas as pd
import os

INDEX_NAME = "news_articles"
CSV_FILE = "news-article-categories.csv"
ELASTICSEARCH_URL = "http://localhost:9200"

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

es = Elasticsearch(ELASTICSEARCH_URL)

def create_index_if_not_exists():
    """检查并创建ES索引"""
    if es.indices.exists(index=INDEX_NAME):
        print(f"Index '{INDEX_NAME}' already exists.")
        return

    mapping = {
        "mappings": {
            "properties": {
                "category": {"type": "keyword"},
                "title": {"type": "text"},
                "body": {"type": "text"},
            }
        }
    }

    es.indices.create(index=INDEX_NAME, body=mapping)
    print(f"Created index '{INDEX_NAME}'.")

def import_data_from_csv():
    """从CSV文件读取数据并导入ES"""
    if not os.path.exists(CSV_FILE):
        print(f"CSV file '{CSV_FILE}' not found. Skipping import.")
        return

    df = pd.read_csv(CSV_FILE, delimiter=",", quotechar='"', encoding="utf-8").fillna('')
    print(f"Loaded {len(df)} rows from CSV.")

    actions = [
        {
            "_index": INDEX_NAME,
            "_source": {
                "category": row["category"],
                "title": row["title"],
                "body": row["body"],
            },
        }
        for _, row in df.iterrows()
    ]

    helpers.bulk(es, actions)
    print(f"Inserted {len(actions)} documents into '{INDEX_NAME}'.")

def ensure_data_ready():
    create_index_if_not_exists()

    count = es.count(index=INDEX_NAME)["count"]
    if count > 0:
        print(f"Index '{INDEX_NAME}' already has {count} documents. Skipping import.")
    else:
        import_data_from_csv()

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"error": "Missing query parameter."}), 400

    search_body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title", "body", "category"],
                "fuzziness": "AUTO" 
            }
        }
    }

    try:
        response = es.search(index=INDEX_NAME, body=search_body)
    except Exception as e:
        print(f"Elasticsearch search error: {e}")
        return jsonify({"error": "Internal server error."}), 500

    hits = response.get('hits', {}).get('hits', [])
    results = [
        {
            "id": hit["_id"],
            "title": hit["_source"].get("title", ""),
            "body": hit["_source"].get("body", ""),
            "category": hit["_source"].get("category", "")
        }
        for hit in hits
    ]

    return jsonify(results)

if __name__ == "__main__":
    ensure_data_ready()
    app.run(host="0.0.0.0", port=5001, debug=True)
