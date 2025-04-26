import React from "react";
import { useNavigate } from "react-router-dom";
import "./ResultsList.css";

function ResultsList({ results }) {
  const navigate = useNavigate();

  const handleClick = (item) => {
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
          <p className="result-body">{truncateText(item.body)}</p>
        </li>
      ))}
    </ul>
  );
}

export default ResultsList;
