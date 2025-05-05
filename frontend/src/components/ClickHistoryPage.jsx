import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

function ClickHistoryPage() {
  const [clicks, setClicks] = useState([]);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem("token");
  const navigate = useNavigate();

  useEffect(() => {
    const fetchClicks = async () => {
      try {
        const res = await fetch("/click-category", {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        const data = await res.json();
        setClicks(data.clicks || []);
      } catch (err) {
        console.error("Error fetching click history:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchClicks();
  }, [token]);

  const handleBack = () => {
    navigate("/");
  };

  return (
    <div className="app-container">
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h1 className="title">Your Interests</h1>
          <button className="logout-button" onClick={handleBack}>Back to Search</button>
        </div>
        {loading ? (
          <p className="message">Loading...</p>
        ) : clicks.length === 0 ? (
          <p className="message">No category click history found.</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0 }}>
            {clicks.map((item) => (
              <li key={item.category} style={{ margin: "0.5rem 0" }}>
                <span className="result-category">{item.category}</span> — clicked {item.click_count} times
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default ClickHistoryPage;
