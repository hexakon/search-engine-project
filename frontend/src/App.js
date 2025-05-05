import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import SearchBar from "./components/SearchBar";
import ResultsList from "./components/ResultsList";
import DetailPage from "./components/DetailPage";
import LoadingDots from "./components/LoadingDots";
import LoginPage from "./components/LoginPage";
import RegisterPage from "./components/RegisterPage";
import ClickHistoryPage from "./components/ClickHistoryPage";
import "./App.css";

function HomePage({ username, onLogout, savedQuery, savedResults, savedPage, savedTotalPages, onSearch }) {
  const [query, setQuery] = useState(savedQuery || "");
  const [results, setResults] = useState(savedResults || []);
  const [currentPage, setCurrentPage] = useState(savedPage || 1);
  const [totalPages, setTotalPages] = useState(savedTotalPages || 0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(!!savedQuery);
  const token = localStorage.getItem("token");
  const navigate = useNavigate();

  const fetchResults = async (searchQuery, page = 1) => {
    if (!searchQuery.trim()) {
      setError("Please enter a search term.");
      setResults([]);
      setTotalPages(0);
      onSearch("", [], 1, 0);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/search?q=${encodeURIComponent(searchQuery)}&page=${page}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch results");
      }

      const data = await response.json();
      setResults(data.results);
      setTotalPages(data.total_pages);
      setCurrentPage(data.page);
      onSearch(searchQuery, data.results, data.page, data.total_pages);
    } catch (err) {
      console.error("Error:", err);
      setError("Failed to fetch results. Try again.");
      setResults([]);
      setTotalPages(0);
      onSearch("", [], 1, 0);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (newQuery) => {
    setQuery(newQuery);
    setHasSearched(true);
    fetchResults(newQuery, 1);
  };

  const handlePageChange = (page) => {
    fetchResults(query, page);
  };

  const renderPagination = () => {
    if (totalPages <= 1) return null;
    const maxPagesToShow = 9;
    const half = Math.floor(maxPagesToShow / 2);
    let startPage = Math.max(1, currentPage - half);
    let endPage = Math.min(totalPages, currentPage + half);
    if (currentPage <= half) endPage = Math.min(totalPages, maxPagesToShow);
    else if (currentPage + half >= totalPages) startPage = Math.max(1, totalPages - maxPagesToShow + 1);

    const buttons = [];
    for (let i = startPage; i <= endPage; i++) {
      buttons.push(
        <button key={i} className={i === currentPage ? "active" : ""} onClick={() => handlePageChange(i)}>
          {i}
        </button>
      );
    }

    return (
      <div className="pagination">
        {currentPage > 1 && <button onClick={() => handlePageChange(currentPage - 1)}>Prev</button>}
        {buttons}
        {currentPage < totalPages && <button onClick={() => handlePageChange(currentPage + 1)}>Next</button>}
      </div>
    );
  };

  return (
    <div className="app-container">
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h1 className="title">Welcome, {username}!</h1>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button className="logout-button" onClick={() => navigate("/click-history")}>View Interests</button>
            <button className="logout-button" onClick={onLogout}>Logout</button>
          </div>
        </div>
        <SearchBar onSearch={handleSearch} initialValue={query} />
        {loading && <LoadingDots />}
        {error && <p className="message error">{error}</p>}
        {!loading && results.length > 0 && (
          <>
            <ResultsList results={results} />
            {renderPagination()}
          </>
        )}
        {!loading && hasSearched && results.length === 0 && <p className="message">No results found.</p>}
      </div>
    </div>
  );
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [username, setUsername] = useState(localStorage.getItem("username"));
  const [savedQuery, setSavedQuery] = useState("");
  const [savedResults, setSavedResults] = useState([]);
  const [savedPage, setSavedPage] = useState(1);
  const [savedTotalPages, setSavedTotalPages] = useState(0);

  const handleLogin = (token, username) => {
    localStorage.setItem("token", token);
    localStorage.setItem("username", username);
    setToken(token);
    setUsername(username);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    setToken(null);
    setUsername(null);
    setSavedQuery("");
    setSavedResults([]);
    setSavedPage(1);
    setSavedTotalPages(0);
  };

  const handleSaveSearch = (query, results, page, totalPages) => {
    setSavedQuery(query);
    setSavedResults(results);
    setSavedPage(page);
    setSavedTotalPages(totalPages);
  };

  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/detail/:id" element={<DetailPage />} />
        <Route path="/click-history" element={<ClickHistoryPage />} />
        <Route
          path="/"
          element={
            token ? (
              <HomePage
                username={username}
                onLogout={handleLogout}
                savedQuery={savedQuery}
                savedResults={savedResults}
                savedPage={savedPage}
                savedTotalPages={savedTotalPages}
                onSearch={handleSaveSearch}
              />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
    </Router>
  );
}

export default App;
