import React from "react";

function ResultsList({ results }) {
  return (
    <ul>
      {results.map((item) => (
        <li key={item.id}>
          <h3>{item.title}</h3>
          <p>{item.content}</p>
        </li>
      ))}
    </ul>
  );
}

export default ResultsList;
