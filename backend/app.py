from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, jwt_required, get_jwt_identity, create_access_token
)
from elasticsearch import Elasticsearch, helpers
from datetime import timedelta, datetime
from collections import Counter
import pandas as pd
import os
import traceback

# Import user models
from user_models import db, bcrypt, User, SearchHistory, CategoryClick

# Configuration
INDEX_NAME = "news_articles"
CSV_FILE = "news-article-categories.csv"
ELASTICSEARCH_URL = "http://localhost:9200"
PAGE_SIZE = 10

# Flask setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "your-secret-key"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)

db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)

# Elasticsearch client
es = Elasticsearch(ELASTICSEARCH_URL)

# ----------------------
# Indexing utilities
# ----------------------

def create_index():
    if es.indices.exists(index=INDEX_NAME):
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


def import_csv_data():
    if not os.path.exists(CSV_FILE):
        return
    df = pd.read_csv(CSV_FILE).fillna('')
    actions = [
        {
            "_index": INDEX_NAME,
            "_source": {
                "category": row["category"],
                "title": row["title"],
                "body": row["body"]
            }
        } for _, row in df.iterrows()
    ]
    helpers.bulk(es, actions)


def ensure_data_ready():
    create_index()
    if es.count(index=INDEX_NAME)["count"] == 0:
        import_csv_data()

# ----------------------
# User preference helpers
# ----------------------

def get_top_search_terms(user_id, top_n_terms=5, lookback=20):
    """
    Fetch the most common search terms from a user's recent search history.
    Returns a list of (term, frequency) pairs.
    """
    recent_records = (
        SearchHistory.query
        .filter_by(user_id=user_id)
        .order_by(SearchHistory.timestamp.desc())
        .limit(lookback)
        .all()
    )
    terms = []
    for rec in recent_records:
        terms.extend(rec.search_text.lower().split())

    most_common = Counter(terms).most_common(top_n_terms)
    return most_common

# ----------------------
# Authentication
# ----------------------

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username, password = data.get("username"), data.get("password")
    if not username or not password:
        return jsonify({"msg": "Missing credentials."}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists."}), 400

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "User registered."}), 200

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username, password = data.get("username"), data.get("password")
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return jsonify(access_token=create_access_token(identity=username)), 200
    return jsonify({"msg": "Invalid credentials."}), 401

# ----------------------
# Search endpoint
# ----------------------

# ============================================
# ENABLE/DISABLE PERSONALIZED SEARCH
#
# This route implements a personalized search that boosts results based on:
#   1. User's top-clicked categories
#   2. User's most frequent past search terms
#
# You can switch between the personalized and basic search implementations by
# commenting out this function (including its decorator) and uncommenting the
# basic, non-personalized search block elsewhere in this file.
# ============================================
@app.route("/search", methods=["GET"])
@jwt_required()
def search():
    """
    Personalized search endpoint.

    Adjustable parameters:
      - PAGE_SIZE (global): number of results per page
      - click_limit: number of top categories to fetch (currently 5)
      - click_weight_base: base weight for category boost (currently 1.0)
      - click_weight_increment: weight per click_count (currently 0.2)
      - history_limit: number of recent searches to consider (get_top_search_terms lookback, currently 20)
      - history_term_limit: number of top search terms (currently 5)
      - history_weight_base: base weight for term boost (currently 0.5)
      - history_weight_increment: weight per term frequency (currently 0.2)
      - fuzziness: Elasticsearch fuzziness strategy (currently "AUTO")
    """
    # Extract and validate the search query
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing query parameter 'q'."}), 400

    # Parse pagination param
    page = int(request.args.get("page", 1))

    # Resolve current user
    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()

    # Record this search in history
    db.session.add(SearchHistory(user_id=user.id, search_text=query))
    db.session.commit()

    # --- Category click boosting ---
    # Fetch the top N categories the user has clicked most
    click_limit = 5  # number of categories to boost
    click_weight_base = 1.0
    click_weight_increment = 0.2

    top_categories = (
        CategoryClick.query
        .filter_by(user_id=user.id)
        .order_by(CategoryClick.click_count.desc())
        .limit(click_limit)
        .all()
    )
    functions = []
    for c in top_categories:
        weight = click_weight_base + c.click_count * click_weight_increment
        functions.append({
            "filter": {"term": {"category": c.category}},
            "weight": weight
        })

    # --- Search history term boosting ---
    # Fetch the most common past search terms
    history_limit = 20      # lookback number of searches
    history_term_limit = 5  # number of terms to boost
    history_weight_base = 0.5
    history_weight_increment = 0.2

    history_terms = get_top_search_terms(
        user_id=user.id,
        top_n_terms=history_term_limit,
        lookback=history_limit
    )
    for term, freq in history_terms:
        weight = history_weight_base + freq * history_weight_increment
        functions.append({
            "filter": {
                "multi_match": {
                    "query": term,
                    "fields": ["title", "body"]
                }
            },
            "weight": weight
        })

    # --- Construct Elasticsearch query ---
    # Fuzziness can be adjusted ('AUTO', '1', '2', etc.)
    fuzziness = "AUTO"

    base_match = {
        "multi_match": {
            "query": query,
            "fields": ["title", "body", "category"],
            "fuzziness": fuzziness
        }
    }

    if functions:
        es_query = {
            "function_score": {
                "query": base_match,
                "functions": functions,
                "score_mode": "sum",    # how to combine function scores
                "boost_mode": "sum"     # how to combine with base score
            }
        }
    else:
        es_query = base_match

    # Pagination parameters
    search_body = {
        "from": (page - 1) * PAGE_SIZE,
        "size": PAGE_SIZE,
        "query": es_query
    }

    # Execute the search
    try:
        response = es.search(index=INDEX_NAME, body=search_body)
    except Exception as e:
        app.logger.error("Search error: %s", e)
        return jsonify({"error": "Elasticsearch error."}), 500

    hits = response.get("hits", {}).get("hits", [])
    total = response.get("hits", {}).get("total", {}).get("value", 0)

    # Format the response
    return jsonify({
        "results": [
            {
                "id": h["_id"],
                "title": h["_source"].get("title", ""),
                "body": h["_source"].get("body", ""),
                "category": h["_source"].get("category", "")
            }
            for h in hits
        ],
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "total_pages": (total + PAGE_SIZE - 1) // PAGE_SIZE
    })
    
# ============================================
# BASIC SEARCH ENDPOINT (Non-Personalized)
#
# This route implements a standard Elasticsearch multi_match search without any personalization.
# It accepts the following URL parameters:
#   - q: the search query string (required)
#   - page: the page number for pagination (optional, defaults to 1)
#
# Principle:
#   1. Build a simple `multi_match` query on fields: title, body, and category.
#   2. Enable `AUTO` fuzziness to handle typos and approximate matching.
#   3. Use `from` and `size` to paginate results, returning total count and total pages.
#
# Usage:
#   - By default, the personalized search route is active.
#   - To enable this non-personalized basic search instead, comment out the personalized
#     @app.route("/search", methods=["GET"]) decorator and its accompanying function,
#     then uncomment the block below (remove the leading # characters).
# ============================================

# @app.route("/search", methods=["GET"])
# @jwt_required()
# def search():
#     # Get the raw query string from the "q" URL parameter and trim whitespace
#     query = request.args.get("q", "").strip()
#     # Get the "page" parameter (default to 1) and convert it to an integer
#     page = int(request.args.get("page", 1))

#     # Return an error if no query was provided
#     if not query:
#         return jsonify({"error": "Missing query parameter 'q'."}), 400

#     # Build a simple Elasticsearch multi_match query without any personalization
#     search_body = {
#         "from": (page - 1) * PAGE_SIZE,  # Calculate offset for pagination
#         "size": PAGE_SIZE,               # Number of results per page
#         "query": {
#             "multi_match": {
#                 "query": query,               # The user's search terms
#                 "fields": ["title", "body", "category"],  # Fields to search
#                 "fuzziness": "AUTO"           # Enable fuzzy matching
#             }
#         }
#     }

#     # Execute the search against the Elasticsearch index
#     try:
#         response = es.search(index=INDEX_NAME, body=search_body)
#     except Exception as e:
#         # Log the error and return a generic message
#         app.logger.error("Search error: %s", e)
#         return jsonify({"error": "Elasticsearch error."}), 500

#     # Extract hits and total count from the response
#     hits = response.get("hits", {}).get("hits", [])
#     total = response.get("hits", {}).get("total", {}).get("value", 0)

#     # Format and return the JSON response
#     return jsonify({
#         "results": [
#             {
#                 "id": h["_id"],
#                 "title": h["_source"].get("title", ""),
#                 "body": h["_source"].get("body", ""),
#                 "category": h["_source"].get("category", "")
#             }
#             for h in hits
#         ],
#         "total": total,                              # Total number of matching documents
#         "page": page,                                # Current page number
#         "page_size": PAGE_SIZE,                      # Number of items per page
#         "total_pages": (total + PAGE_SIZE - 1) // PAGE_SIZE  # Compute total pages
#     })


# ----------------------
# Click Tracking & History
# ----------------------
@app.route("/search-history", methods=["GET"])
@jwt_required()
def get_search_history():
    # Determine if all records should be fetched (word cloud mode)
    fetch_all = request.args.get("all", "false").lower() == "true"
    page = int(request.args.get("page", 1))
    page_size = 10

    # Get the current user
    user = User.query.filter_by(username=get_jwt_identity()).first()

    # Build base query sorted by timestamp descending
    base_q = (
        SearchHistory.query
        .filter_by(user_id=user.id)
        .order_by(SearchHistory.timestamp.desc())
    )

    if fetch_all:
        # Fetch all entries without pagination
        entries = base_q.all()
        total = len(entries)
        total_pages = 1
        page = 1
    else:
        # Paginate the query
        total = base_q.count()
        total_pages = (total + page_size - 1) // page_size
        entries = (
            base_q
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

    # Serialize and return the response
    return jsonify({
        "history": [
            {"search_text": e.search_text, "timestamp": e.timestamp.isoformat()}
            for e in entries
        ],
        "total": total,
        "page": page,
        "total_pages": total_pages
    }), 200


@app.route("/click-category", methods=["POST"])
@jwt_required()
def click_category():
    data = request.get_json()
    category = data.get("category")
    if not category:
        return jsonify({"error": "Missing category."}), 400

    user = User.query.filter_by(username=get_jwt_identity()).first()
    record = CategoryClick.query.filter_by(user_id=user.id, category=category).first()
    if record:
        record.click_count += 1
    else:
        db.session.add(CategoryClick(user_id=user.id, category=category, click_count=1))
    db.session.commit()
    return jsonify({"message": "Click recorded."}), 200

@app.route("/click-category", methods=["GET"])
@jwt_required()
def get_clicks():
    user = User.query.filter_by(username=get_jwt_identity()).first()
    clicks = CategoryClick.query.filter_by(user_id=user.id).order_by(CategoryClick.click_count.desc()).all()
    return jsonify({
        "clicks": [{"category": c.category, "click_count": c.click_count} for c in clicks]
    }), 200

@app.route("/clear-history", methods=["POST"])
@jwt_required()
def clear_history():
    user = User.query.filter_by(username=get_jwt_identity()).first()
    try:
        SearchHistory.query.filter(SearchHistory.user_id == user.id).delete()
        CategoryClick.query.filter(CategoryClick.user_id == user.id).delete()
        db.session.commit()
        return jsonify({"message": "History cleared."}), 200
    except Exception as e:
        print("Error clearing history:", e)
        traceback.print_exc()
        return jsonify({"error": "Failed to clear history."}), 500

# ----------------------
# Entry Point
# ----------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        ensure_data_ready()
    app.run(host="0.0.0.0", port=5001, debug=True)
