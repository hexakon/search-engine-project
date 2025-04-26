import React, { useState } from "react";
import SearchBar from "./components/SearchBar";
import ResultsList from "./components/ResultsList";

function App() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async (query) => {
    if (!query.trim()) {
      setError("Please enter a search term.");
      setResults([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/search?q=${encodeURIComponent(query)}`, {
        method: "GET",
        mode: "cors",
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      console.error("Fetch error:", err);
      setError("Failed to fetch results. Please try again later.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const renderContent = () => {
    if (loading) {
      return <p style={styles.message}>Loading...</p>;
    }

    if (error) {
      return <p style={{ ...styles.message, color: "red" }}>{error}</p>;
    }

    if (results.length === 0) {
      return <p style={styles.message}>No results found. Try another search.</p>;
    }

    return <ResultsList results={results} />;
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>News Search Engine</h1>
      <SearchBar onSearch={handleSearch} />
      {renderContent()}
    </div>
  );
}

const styles = {
  container: {
    padding: "2rem",
    fontFamily: "Arial, sans-serif",
    maxWidth: "800px",
    margin: "0 auto",
  },
  title: {
    textAlign: "center",
    marginBottom: "2rem",
  },
  message: {
    textAlign: "center",
    marginTop: "2rem",
    fontSize: "1.1rem",
  },
};

export default App;
