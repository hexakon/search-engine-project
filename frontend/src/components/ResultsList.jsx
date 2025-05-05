import React from "react";
import { useNavigate } from "react-router-dom";
import "./ResultsList.css";

function ResultsList({ results }) {
  const navigate = useNavigate();
  const token = localStorage.getItem("token");

  const handleClick = async (item) => {
    // Send category click to backend
    try {
      await fetch("/click-category", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ category: item.category }),
      });
    } catch (err) {
      console.error("Failed to record category click:", err);
    }

    // Navigate to detail page
    navigate(`/detail/${item.id}`, { state: { item } });
  };

  const truncateText = (text) => {
    const maxLength = 200;
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength) + "...";
  };

  return (
    <ul className="results-list">
      {results.map((item) => (
        <li key={item.id} className="result-item" onClick={() => handleClick(item)}>
          <h3 className="result-title">{item.title}</h3>
          <span className="result-category">{item.category}</span>
          <p className="result-body">{truncateText(item.body)}</p>
        </li>
      ))}
    </ul>
  );
}

export default ResultsList;
