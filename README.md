# News Search Engine Project

This project is a simple news search engine built with:

- **Backend**: Flask + Elasticsearch
- **Frontend**: React
- **Dataset**: News Article Category Dataset (`news-article-categories.csv`)

Users can search news articles by keywords across title, body, and category fields.

---

## 📁 Project Structure

```
search-engine-project/
├── backend/
│   ├── app.py
│   ├── news-article-categories.csv
│   ├── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── SearchBar.jsx
│   │   │   ├── ResultsList.jsx
│   ├── package.json
```

---

## 🚀 How to Run

### 1. Set up Elasticsearch
Make sure Elasticsearch 7.17.x is running locally on port 9200.

If you already have Docker installed, you can quickly start Elasticsearch with:

```bash
docker run -p 9200:9200 -e "discovery.type=single-node" elasticsearch:7.17.0
```
Note: You may need to first pull the image using

```bash
docker pull elasticsearch:7.17.0
```

If you do not have Docker, you can install Elasticsearch manually:

1. Download Elasticsearch 7.17 from the official website:
https://www.elastic.co/downloads/past-releases/elasticsearch-7-17-0 

Extract the archive and start Elasticsearch manually:

```bash
cd elasticsearch-7.17.0
./bin/elasticsearch
```

Make sure Elasticsearch is running and accessible at http://localhost:9200/ before starting the backend.



### 2. Set up the Backend

Navigate to the backend directory:

```bash
cd backend
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the Flask server:

```bash
python app.py
```

- The backend server will run on `http://localhost:5001/`.
- It will automatically load the CSV dataset into Elasticsearch if necessary.

### 3. Set up the Frontend

Navigate to the frontend directory:

```bash
cd frontend
```

Install Node.js dependencies:

```bash
npm install
```

Ensure the `proxy` field in `frontend/package.json` points to the backend:

```json
"proxy": "http://localhost:5001"
```

Start the React development server:

```bash
npm start
```

The application will open at `http://localhost:3000/`.

---

## 🌟 Features

- Full-text search on news titles, bodies, and categories.
- Fuzzy search enabled (tolerates minor typos).
- Loading, error, and empty result handling in the frontend.
- Automatic index creation and data import for Elasticsearch.

---

## 📚 API Reference

### `GET /search?q=your_query`

**Query Parameters:**
- `q` (required): Search keyword.

**Response:**

```json
[
  {
    "id": "document_id",
    "title": "News Title",
    "body": "Full content of the article",
    "category": "Category name"
  },
  ...
]
```

Example request:

```
GET http://localhost:5001/search?q=climate
```