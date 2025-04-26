import React from "react";
import "./LoadingDots.css"; // Separate CSS for clean animation

function LoadingDots() {
  return (
    <div className="dots-loading-container">
      <div className="dot"></div>
      <div className="dot"></div>
      <div className="dot"></div>
    </div>
  );
}

export default LoadingDots;
