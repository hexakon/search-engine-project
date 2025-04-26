import React, { useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import SearchBar from "./components/SearchBar";
import ResultsList from "./components/ResultsList";
import DetailPage from "./components/DetailPage";
import LoadingDots from "./components/LoadingDots";
import "./App.css";

function HomePage({ savedQuery, savedResults, savedPage, savedTotalPages, onSearch }) {
  const [query, setQuery] = useState(savedQuery || "");
  const [results, setResults] = useState(savedResults || []);
  const [currentPage, setCurrentPage] = useState(savedPage || 1);
  const [totalPages, setTotalPages] = useState(savedTotalPages || 0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  // Fetch search results from backend
  const fetchResults = async (searchQuery, page = 1) => {
    if (!searchQuery.trim()) {
      setError("Please enter a search term.");
      setResults([]);
      setTotalPages(0);
      onSearch("", [], 1, 0); // reset in parent too
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/search?q=${encodeURIComponent(searchQuery)}&page=${page}`, {
        method: "GET",
        mode: "cors",
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      setResults(data.results);
      setTotalPages(data.total_pages);
      setCurrentPage(data.page);
      onSearch(searchQuery, data.results, data.page, data.total_pages); // save all
    } catch (err) {
      console.error("Fetch error:", err);
      setError("Failed to fetch results. Please try again later.");
      setResults([]);
      setTotalPages(0);
      onSearch("", [], 1, 0);
    } finally {
      setLoading(false);
    }
  };

  // Handle a new search
  const handleSearch = (newQuery) => {
    setQuery(newQuery);
    setHasSearched(true);  // mark as searched
    fetchResults(newQuery, 1);
  };

  // Handle page change
  const handlePageChange = (page) => {
    fetchResults(query, page);
  };

  // Render pagination controls
  const renderPagination = () => {
    if (totalPages <= 1) return null;

    const maxPagesToShow = 9;
    const half = Math.floor(maxPagesToShow / 2);

    let startPage = Math.max(1, currentPage - half);
    let endPage = Math.min(totalPages, currentPage + half);

    if (currentPage <= half) {
      endPage = Math.min(totalPages, maxPagesToShow);
    } else if (currentPage + half >= totalPages) {
      startPage = Math.max(1, totalPages - maxPagesToShow + 1);
    }

    const pageButtons = [];
    for (let i = startPage; i <= endPage; i++) {
      pageButtons.push(
        <button
          key={i}
          className={i === currentPage ? "active" : ""}
          onClick={() => handlePageChange(i)}
        >
          {i}
        </button>
      );
    }

    return (
      <div className="pagination">
        {currentPage > 1 && (
          <button onClick={() => handlePageChange(currentPage - 1)}>Prev</button>
        )}
        {pageButtons}
        {currentPage < totalPages && (
          <button onClick={() => handlePageChange(currentPage + 1)}>Next</button>
        )}
      </div>
    );
  };

  // Render search results or loading/error messages
  const renderContent = () => {
    if (loading) {
      return <LoadingDots />;
    }

    if (error) {
      return <p className="message error">{error}</p>;
    }

    if (results.length === 0) {
      if (hasSearched) {
        return <p className="message">No results found. Try another search.</p>;
      } else {
        return null;  // No message at all if never searched
      }
    }

    return (
      <>
        <ResultsList results={results} />
        {loading && <LoadingDots />}  {/* Only show dots while loading */}
        {renderPagination()}
      </>
    );
  };

  return (
    <div className="app-container">
      <div className="card">
        <h1 className="title">News Search Engine</h1>
        <SearchBar onSearch={handleSearch} />
        {renderContent()}
      </div>
    </div>
  );
}

function App() {
  // Global saved search states
  const [savedQuery, setSavedQuery] = useState("");
  const [savedResults, setSavedResults] = useState([]);
  const [savedPage, setSavedPage] = useState(1);
  const [savedTotalPages, setSavedTotalPages] = useState(0);

  // Save search results globally
  const handleSaveSearch = (query, results, page, totalPages) => {
    setSavedQuery(query);
    setSavedResults(results);
    setSavedPage(page);
    setSavedTotalPages(totalPages);
  };

  return (
    <Router>
      <Routes>
        <Route
          path="/"
          element={
            <HomePage
              savedQuery={savedQuery}
              savedResults={savedResults}
              savedPage={savedPage}
              savedTotalPages={savedTotalPages}
              onSearch={handleSaveSearch}
            />
          }
        />
        <Route path="/detail/:id" element={<DetailPage />} />
      </Routes>
    </Router>
  );
}

export default App;
