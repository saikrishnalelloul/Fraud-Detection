import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from "chart.js";
import { Pie } from "react-chartjs-2";
import "./App.css";

ChartJS.register(ArcElement, Tooltip, Legend);

// ===== Helpers =====
const formatAmount = (a) => {
  if (a === null || a === undefined || a === "") return "-";
  const n = Number(a);
  if (Number.isNaN(n)) return a;
  return (
    "₹" +
    n.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
};

const formatTime = (t) => {
  if (!t) return "-";
  try {
    const d = new Date(t);
    return isNaN(d.getTime()) ? t : d.toLocaleString();
  } catch {
    return t;
  }
};

const statusFrom = (tx) => {
  if ("is_fraud" in tx) return tx.is_fraud ? "Fraud" : "Normal";

  if ("prediction" in tx) {
    const value = tx.prediction;
    if (typeof value === "string") {
      return value.toLowerCase() === "fraud" ? "Fraud" : "Normal";
    }
    if (value != null) {
      return String(value).toLowerCase() === "fraud" ? "Fraud" : "Normal";
    }
  }

  if ("status" in tx) return tx.status;

  return "Unknown";
};

function App() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [stats, setStats] = useState({ total: 0, frauds: 0 });
  const [filters, setFilters] = useState({
    userId: "",
    amount: "",
  });
  const [appliedFilters, setAppliedFilters] = useState({
    userId: "",
    amount: "",
  });

  const fetchTransactions = async () => {
    try {
      setRefreshing(true);
      const res = await axios.get("http://127.0.0.1:5000/transactions?n=20");
      const payload = res.data || {};
      const items = Array.isArray(payload) ? payload : payload.items || [];
      const meta = Array.isArray(payload) ? null : payload.meta || {};

      setTransactions(items);
      setStats({
        total: meta?.total ?? items.length,
        frauds:
          meta?.frauds ??
          items.filter((tx) => statusFrom(tx) === "Fraud").length,
      });
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

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };

  const handleValidate = (event) => {
    event.preventDefault();
    setAppliedFilters(filters);
  };

  const handleReset = () => {
    const reset = { userId: "", amount: "" };
    setFilters(reset);
    setAppliedFilters(reset);
  };

  const filteredTransactions = useMemo(() => {
    if (!appliedFilters.userId && !appliedFilters.amount) {
      return transactions;
    }

    const userIdQuery = appliedFilters.userId.trim().toLowerCase();
    const amountThreshold = parseFloat(appliedFilters.amount);

    return transactions.filter((tx) => {
      const userId = (tx.user_id ?? tx.userId ?? "").toString().toLowerCase();
      const amount = parseFloat(tx.amount);

      const matchesUser = userIdQuery ? userId.includes(userIdQuery) : true;
      const matchesAmount = Number.isFinite(amountThreshold)
        ? Number.isFinite(amount) && amount >= amountThreshold
        : true;

      return matchesUser && matchesAmount;
    });
  }, [transactions, appliedFilters]);

  const total = stats.total ?? transactions.length;
  const fraudCount = stats.frauds ?? 0;
  const fraudPercent = total > 0 ? ((fraudCount / total) * 100).toFixed(1) : 0;
  const validCount = Math.max(total - fraudCount, 0);

  const chartData = useMemo(() => {
    if (total === 0) {
      return null;
    }

    return {
      labels: ["Fraud", "Valid"],
      datasets: [
        {
          data: [fraudCount, validCount],
          backgroundColor: ["#ff4d4f", "#28a745"],
          borderWidth: 0,
          hoverOffset: 8,
        },
      ],
    };
  }, [fraudCount, validCount, total]);

  const chartOptions = useMemo(
    () => ({
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const label = context.label || "";
              const value = context.parsed;
              const percent = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
              return `${label}: ${value} (${percent}%)`;
            },
          },
          backgroundColor: "#161b22",
          borderColor: "#30363d",
          borderWidth: 1,
        },
      },
      responsive: true,
      maintainAspectRatio: false,
      cutout: "55%",
    }),
    [total]
  );

  return (
    <div className="container">
      <div className="header">
        <h1 className="title">💳 Fraud Detection Dashboard</h1>
        <div className="status-bar">
          <span className="live-dot"></span> LIVE
          {refreshing && <span className="refresh">⟳</span>}
        </div>
      </div>

      <div className="dashboard-top">
        <div className="left-column">
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

          <div className="form-card">
            <h3>Transaction Lookup</h3>
            <form onSubmit={handleValidate}>
              <div className="form-grid">
                <div className="input-group">
                  <label htmlFor="userId">User ID</label>
                  <input
                    id="userId"
                    name="userId"
                    placeholder="Enter user ID"
                    value={filters.userId}
                    onChange={handleInputChange}
                  />
                </div>
                <div className="input-group">
                  <label htmlFor="amount">Amount (₹)</label>
                  <input
                    id="amount"
                    name="amount"
                    placeholder="Enter amount"
                    value={filters.amount}
                    onChange={handleInputChange}
                  />
                </div>
              </div>
              <div className="actions">
                <button type="submit" className="primary-btn">
                  Validate
                </button>
                <button type="button" className="secondary-btn" onClick={handleReset}>
                  Reset
                </button>
              </div>
            </form>
          </div>
        </div>

        <div className="chart-card">
          <h3>Transaction Distribution</h3>
          <div className="chart-wrapper">
            {chartData ? (
              <Pie data={chartData} options={chartOptions} />
            ) : (
              <p className="chart-empty">No transactions yet</p>
            )}
          </div>
          <div className="chart-legend">
            <span>
              <span className="legend-dot fraud"></span> Fraud
            </span>
            <span>
              <span className="legend-dot valid"></span> Valid
            </span>
          </div>
        </div>
      </div>

      {/* ===== Transaction Table ===== */}
      {loading ? (
        <p>Loading transactions ...</p>
      ) : (
        <div className={`table-wrapper fade-in ${refreshing ? "dim" : ""}`}>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Transaction ID</th>
                <th>User ID</th>
                <th>Amount</th>
                <th>Time</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredTransactions.map((tx, idx) => {
                const id = tx.id ?? tx.rowid ?? tx.rowId ?? "—";
                let transactionId = tx.transaction_id ?? tx.transactionId ?? "—";
                const userId = tx.user_id ?? tx.userId ?? "—";
                let amount = tx.amount ?? tx.amount_value ?? tx.amountValue ?? "-";
                // Detect swapped data: historical records sometimes stored UUID in `amount`
                if (
                  typeof amount === "string" &&
                  amount.includes("-") &&
                  (typeof transactionId === "number" || /^[0-9]+$/.test(String(transactionId)))
                ) {
                  const swapped = amount;
                  amount = transactionId;
                  transactionId = swapped;
                }
                const time = tx.time ?? tx.timestamp ?? "-";
                const status = statusFrom(tx);
                const statusClass = status === "Fraud" ? "status-pill fraud" : "status-pill valid";

                return (
                  <tr key={transactionId !== "—" ? transactionId : `row-${id}-${idx}`}>
                    <td>{id}</td>
                    <td>{transactionId}</td>
                    <td>{userId}</td>
                    <td>{formatAmount(amount)}</td>
                    <td>{formatTime(time)}</td>
                    <td>
                      <span className={statusClass}>{status}</span>
                    </td>
                  </tr>
                );
              })}
              {filteredTransactions.length === 0 && (
                <tr>
                  <td colSpan="6" className="empty-state">
                    No transactions match your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default App;
