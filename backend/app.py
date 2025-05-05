from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, jwt_required, get_jwt_identity, create_access_token
)
from elasticsearch import Elasticsearch, helpers
import pandas as pd
import os
from datetime import timedelta

# Import user models
from user_models import db, bcrypt, User, SearchHistory, CategoryClick

# Configuration
INDEX_NAME = "news_articles"
CSV_FILE = "news-article-categories.csv"
ELASTICSEARCH_URL = "http://localhost:9200"
PAGE_SIZE = 10

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# App config
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "your-secret-key"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)

# Init extensions
db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)

# Connect to Elasticsearch
es = Elasticsearch(ELASTICSEARCH_URL)

# ----------------------
# Index Initialization
# ----------------------

def create_index():
    """Create Elasticsearch index with mapping if not already exists."""
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

def import_csv_data():
    """Import CSV file into Elasticsearch index."""
    if not os.path.exists(CSV_FILE):
        print(f"CSV file '{CSV_FILE}' not found. Skipping import.")
        return

    df = pd.read_csv(CSV_FILE).fillna('')
    print(f"Loaded {len(df)} rows from CSV.")

    actions = [
        {
            "_index": INDEX_NAME,
            "_source": {
                "category": row["category"],
                "title": row["title"],
                "body": row["body"],
            }
        } for _, row in df.iterrows()
    ]

    helpers.bulk(es, actions)
    print(f"Inserted {len(actions)} documents into '{INDEX_NAME}'.")

def ensure_data_ready():
    """Ensure index and data are ready."""
    create_index()
    count = es.count(index=INDEX_NAME)["count"]
    if count == 0:
        import_csv_data()
    else:
        print(f"Index already has {count} documents.")

# ----------------------
# Authentication Routes
# ----------------------

@app.route("/register", methods=["POST"])
def register():
    """Register a new user with username and password."""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"msg": "Missing username or password."}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already taken."}), 400

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "User registered successfully."}), 200

@app.route("/login", methods=["POST"])
def login():
    """Login user and return JWT token."""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        token = create_access_token(identity=username)
        return jsonify(access_token=token), 200
    return jsonify({"msg": "Invalid credentials."}), 401

# ----------------------
# Search & Click Routes
# ----------------------


# --------------------------------------------------------------
# The following code implements a standard search interface
# using Elasticsearch's multi_match query across title, body,
# and category fields, with fuzziness enabled.
# 
# It does NOT apply any personalization or user-specific ranking.
# 
# You can uncomment this function to compare with the personalized
# version of search and test standard relevance results.
# --------------------------------------------------------------


# @app.route("/search", methods=["GET"])
# @jwt_required()
# def search():
#     """Perform full-text search in Elasticsearch and log query."""
#     query = request.args.get("q", "").strip()
#     page = int(request.args.get("page", 1))
#     if not query:
#         return jsonify({"error": "Missing query parameter 'q'."}), 400

#     username = get_jwt_identity()
#     user = User.query.filter_by(username=username).first()
#     if user:
#         db.session.add(SearchHistory(user_id=user.id, query=query))
#         db.session.commit()

#     search_body = {
#         "from": (page - 1) * PAGE_SIZE,
#         "size": PAGE_SIZE,
#         "query": {
#             "multi_match": {
#                 "query": query,
#                 "fields": ["title", "body", "category"],
#                 "fuzziness": "AUTO"
#             }
#         }
#     }

#     try:
#         response = es.search(index=INDEX_NAME, body=search_body)
#     except Exception as e:
#         print(f"Search error: {e}")
#         return jsonify({"error": "Elasticsearch error."}), 500

#     hits = response.get("hits", {}).get("hits", [])
#     total = response.get("hits", {}).get("total", {}).get("value", 0)

#     results = [
#         {
#             "id": hit["_id"],
#             "title": hit["_source"].get("title", ""),
#             "body": hit["_source"].get("body", ""),
#             "category": hit["_source"].get("category", "")
#         }
#         for hit in hits
#     ]

#     return jsonify({
#         "results": results,
#         "total": total,
#         "page": page,
#         "page_size": PAGE_SIZE,
#         "total_pages": (total + PAGE_SIZE - 1) // PAGE_SIZE
#     })


# --------------------------------------------------------------
# The following function implements a personalized search.
# 
# It retrieves the user's top clicked categories from the database
# and uses Elasticsearch's `function_score` to boost documents
# that match those preferred categories.
#
# The more frequently a user clicks on a category, the higher
# the weight assigned to it—this biases the search ranking toward
# the user's interests, while still respecting the original query.
#
# You can compare this personalized result with the standard one
# by toggling the two search endpoints.
# --------------------------------------------------------------

@app.route("/search", methods=["GET"])
@jwt_required()
def search():
    """Perform personalized search using Elasticsearch and user click history."""
    query = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    if not query:
        return jsonify({"error": "Missing query parameter 'q'."}), 400

    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()

    # Save search history
    if user:
        db.session.add(SearchHistory(user_id=user.id, query=query))
        db.session.commit()

    # Get user's top N clicked categories
    top_categories = (
        CategoryClick.query
        .filter_by(user_id=user.id)
        .order_by(CategoryClick.click_count.desc())
        .limit(5)
        .all()
    )

    # Build personalization functions
    functions = []
    for cat in top_categories:
        weight = 1.0 + cat.click_count * 0.2  # More clicks → more weight
        functions.append({
            "filter": {"term": {"category": cat.category}},
            "weight": weight
        })

    # Compose query with function_score if any personal weights exist
    if functions:
        es_query = {
            "function_score": {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title", "body", "category"],
                        "fuzziness": "AUTO"
                    }
                },
                "functions": functions,
                "score_mode": "sum",
                "boost_mode": "sum"
            }
        }
    else:
        es_query = {
            "multi_match": {
                "query": query,
                "fields": ["title", "body", "category"],
                "fuzziness": "AUTO"
            }
        }

    # Construct search body
    search_body = {
        "from": (page - 1) * PAGE_SIZE,
        "size": PAGE_SIZE,
        "query": es_query
    }

    try:
        response = es.search(index=INDEX_NAME, body=search_body)
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({"error": "Elasticsearch error."}), 500

    hits = response.get("hits", {}).get("hits", [])
    total = response.get("hits", {}).get("total", {}).get("value", 0)

    results = [
        {
            "id": hit["_id"],
            "title": hit["_source"].get("title", ""),
            "body": hit["_source"].get("body", ""),
            "category": hit["_source"].get("category", "")
        }
        for hit in hits
    ]

    return jsonify({
        "results": results,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "total_pages": (total + PAGE_SIZE - 1) // PAGE_SIZE
    })


@app.route("/click-category", methods=["POST"])
@jwt_required()
def click_category():
    """Log category click when user views a specific item."""
    data = request.get_json()
    category = data.get("category")
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()

    if not category or not user:
        return jsonify({"error": "Missing category or user."}), 400

    click = CategoryClick.query.filter_by(user_id=user.id, category=category).first()
    if click:
        click.click_count += 1
    else:
        click = CategoryClick(user_id=user.id, category=category, click_count=1)
        db.session.add(click)
    db.session.commit()

    return jsonify({"message": "Click recorded."}), 200

@app.route("/click-category", methods=["GET"])
@jwt_required()
def get_click_history():
    """Retrieve user's click history (categories and counts), ordered by count descending."""
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found."}), 404

    clicks = (
        CategoryClick.query
        .filter_by(user_id=user.id)
        .order_by(CategoryClick.click_count.desc()) 
        .all()
    )
    data = [{"category": c.category, "click_count": c.click_count} for c in clicks]
    return jsonify({"clicks": data}), 200

@app.route("/recommend", methods=["GET"])
@jwt_required()
def recommend():
    """Recommend articles based on most clicked categories."""
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found."}), 404

    top_cats = (
        CategoryClick.query
        .filter_by(user_id=user.id)
        .order_by(CategoryClick.click_count.desc())
        .limit(3).all()
    )

    if not top_cats:
        return jsonify({"message": "No category click history."}), 200

    search_body = {
        "size": 10,
        "query": {
            "bool": {
                "should": [
                    {"match": {"category": c.category}} for c in top_cats
                ]
            }
        }
    }

    try:
        response = es.search(index=INDEX_NAME, body=search_body)
    except Exception as e:
        print(f"Recommend error: {e}")
        return jsonify({"error": "Internal server error."}), 500

    hits = response.get("hits", {}).get("hits", [])
    results = [
        {
            "id": hit["_id"],
            "title": hit["_source"].get("title", ""),
            "body": hit["_source"].get("body", ""),
            "category": hit["_source"].get("category", "")
        }
        for hit in hits
    ]

    return jsonify({
        "recommended_categories": [c.category for c in top_cats],
        "results": results
    })

# ----------------------
# Main Entry
# ----------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        ensure_data_ready()

    app.run(host="0.0.0.0", port=5001, debug=True)
