import React, { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchTransactions = async () => {
    try {
      setRefreshing(true);
      const res = await axios.get("http://127.0.0.1:5000/transactions?n=20");
      setTransactions(res.data);
      setLoading(false);
    } catch (err) {
      console.error("Error fetching transactions:", err);
    } finally {
      setTimeout(() => setRefreshing(false), 400);
    }
  };

  useEffect(() => {
    fetchTransactions();
    const interval = setInterval(fetchTransactions, 5000);
    return () => clearInterval(interval);
  }, []);

  // ===== Summary calculations =====
  const total = transactions.length;
  const fraudCount = transactions.filter(tx => tx.prediction === "fraud").length;
  const fraudPercent = total > 0 ? ((fraudCount / total) * 100).toFixed(1) : 0;

  return (
    <div className="container">
      <div className="header">
        <h1 className="title">💳 Fraud Detection Dashboard</h1>
        <div className="status-bar">
          <span className="live-dot"></span> LIVE
          {refreshing && <span className="refresh">⟳</span>}
        </div>
      </div>

      {/* ===== Summary cards ===== */}
      <div className="summary">
        <div className="card total">
          <h3>Total</h3>
          <p>{total}</p>
        </div>
        <div className="card fraud">
          <h3>Frauds</h3>
          <p>{fraudCount}</p>
        </div>
        <div className="card percent">
          <h3>Fraud %</h3>
          <p>{fraudPercent}%</p>
        </div>
      </div>

      {/* ===== Transaction Table ===== */}
      {loading ? (
        <p>Loading transactions ...</p>
      ) : (
        <table className={`fade-in ${refreshing ? "dim" : ""}`}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Amount (₹)</th>
              <th>Location</th>
              <th>Device</th>
              <th>Time</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx) => (
              <tr
                key={tx.transaction_id}
                className={tx.prediction === "fraud" ? "fraud" : "normal"}
              >
                <td>{tx.transaction_id}</td>
                <td>{tx.amount}</td>
                <td>{tx.location}</td>
                <td>{tx.device}</td>
                <td>{tx.time}</td>
                <td>{tx.prediction}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default App;
