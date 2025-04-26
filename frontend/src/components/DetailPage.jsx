import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "./DetailPage.css";

function DetailPage() {
  const { state } = useLocation();
  const navigate = useNavigate();

  if (!state || !state.item) {
    return <p style={{ textAlign: "center", marginTop: "2rem", color: "#ccc" }}>No data found.</p>;
  }

  const { title, body } = state.item;

  const splitParagraphs = (text) => {
    return text
      .split(/(?<=[.!?])\s+/) // Split by sentence-ending punctuation
      .map((sentence, idx) => <p key={idx}>{sentence}</p>);
  };

  return (
    <div className="detail-container fade-in">
      <button className="back-button" onClick={() => navigate(-1)}>
        ← Back
      </button>
      <h1 className="detail-title">{title}</h1>
      <div className="detail-body">{splitParagraphs(body)}</div>
    </div>
  );
}

export default DetailPage;
