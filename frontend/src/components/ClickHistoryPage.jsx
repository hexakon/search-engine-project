import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";
import "./ClickHistoryPage.css";

function ClickHistoryPage() {
  const [clicks, setClicks] = useState([]);
  const [searchHistory, setSearchHistory] = useState([]);
  const [loadingClicks, setLoadingClicks] = useState(true);
  const [loadingSearch, setLoadingSearch] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showCategoryChart, setShowCategoryChart] = useState(false);

  const token = localStorage.getItem("token");
  const navigate = useNavigate();

  // Load category clicks
  useEffect(() => {
    (async () => {
      setLoadingClicks(true);
      try {
        const res = await fetch("/click-category", { headers: { Authorization: `Bearer ${token}` } });
        const data = await res.json();
        setClicks(data.clicks || []);
      } catch (err) {
        console.error("Error loading categories:", err);
      }
      setLoadingClicks(false);
    })();
  }, []);

  // Load search history pages
  useEffect(() => {
    (async () => {
      setLoadingSearch(true);
      try {
        const res = await fetch(`/search-history?page=${page}`, { headers: { Authorization: `Bearer ${token}` } });
        const data = await res.json();
        setSearchHistory(data.history || []);
        setTotalPages(data.total_pages || 1);
      } catch (err) {
        console.error("Error loading search history:", err);
      }
      setLoadingSearch(false);
    })();
  }, [page]);

  // Pagination
  const prevPage = () => setPage(p => Math.max(1, p - 1));
  const nextPage = () => setPage(p => Math.min(totalPages, p + 1));

  // Clear history
  const handleClearHistory = async () => {
    if (!window.confirm("Are you sure you want to clear all history?")) return;
    try {
      const res = await fetch("/clear-history", { method: "POST", headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        setClicks([]);
        setSearchHistory([]);
        setPage(1);
        setTotalPages(1);
      }
    } catch (err) {
      console.error("Error clearing history:", err);
    }
  };

  return (
    <div className="history-container">
      <div className="history-card">
        <div className="history-header">
          <h1 className="history-title">Your History</h1>
          <div>
            <button className="history-back-button" onClick={() => navigate("/")}>Back</button>
            <button className="history-clear-button" onClick={handleClearHistory}>Clear</button>
          </div>
        </div>

        {/* Categories Section */}
        <section className="history-section">
          <div className="history-section-header">
            <h2 className="history-subtitle">Top Categories</h2>
            <button className="toggle-button" onClick={() => setShowCategoryChart(c => !c)}>
              {showCategoryChart ? "List View" : "Chart View"}
            </button>
          </div>

          {loadingClicks ? (
            <p className="history-message">Loading categories...</p>
          ) : showCategoryChart ? (
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={clicks} margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
                  <defs>
                    <linearGradient id="purpleGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.8} />
                      <stop offset="100%" stopColor="#4c1d95" stopOpacity={0.6} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#2d2d45" vertical={false} />
                  <XAxis dataKey="category" tick={{ fill: "#ccc", fontSize: 12 }} axisLine={{ stroke: "#3f3f5a" }} />
                  <YAxis tick={{ fill: "#ccc", fontSize: 12 }} axisLine={{ stroke: "#3f3f5a" }} />
                  <Tooltip wrapperStyle={{ backgroundColor: "#2d2d45", borderColor: "#3f3f5a" }} itemStyle={{ color: "#fff" }} labelStyle={{ color: "#aaa" }} cursor={{ fill: "rgba(76,61,128,0.2)" }} />
                  <Bar dataKey="click_count" fill="url(#purpleGradient)" radius={[4, 4, 0, 0]} barSize={35} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : clicks.length ? (
            <ul className="history-list">
              {clicks.map(item => (
                <li key={item.category} className="history-list-item">
                  <span className="history-category-tag">{item.category}</span>
                  {/* Display click count with label */}
                  <span className="history-click-label">clicked</span>
                  <span className="history-count"> {item.click_count} </span>
                  <span className="history-click-label">times</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="history-message">No category data.</p>
          )}
        </section>

        {/* Search Section */}
        <section className="history-section">
          <h2 className="history-subtitle">Search History</h2>
          {loadingSearch ? (
            <p className="history-message">Loading searches...</p>
          ) : searchHistory.length ? (
            <>
              <ul className="history-list">
                {searchHistory.map((item, i) => (
                  <li key={i} className="history-list-item">
                    <span>{item.search_text}</span>
                    <span className="history-timestamp">{new Date(item.timestamp).toLocaleString()}</span>
                  </li>
                ))}
              </ul>
              <div className="pagination">
                <button onClick={prevPage} disabled={page === 1}>&lt;</button>
                <span>Page {page}/{totalPages}</span>
                <button onClick={nextPage} disabled={page === totalPages}>&gt;</button>
              </div>
            </>
          ) : (
            <p className="history-message">No search records.</p>
          )}
        </section>
      </div>
    </div>
  );
}

export default ClickHistoryPage;
