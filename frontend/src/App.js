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

const StatCard = ({ label, value, tone, badge }) => {
  const symbol = badge || (label ? label.charAt(0).toUpperCase() : "?");
  return (
    <div className={`stat-card tone-${tone}`}>
      <div className="stat-card-top">
        <span className="stat-icon" aria-hidden="true">
          {symbol}
        </span>
        <span className="stat-label">{label}</span>
      </div>
      <div className="stat-value">{value}</div>
    </div>
  );
};

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
    location: "",
  });
  const [appliedFilters, setAppliedFilters] = useState({
    userId: "",
    amount: "",
    location: "",
  });
  const [validationResult, setValidationResult] = useState(null);
  const [validationError, setValidationError] = useState(null);
  const [validating, setValidating] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [hasValidated, setHasValidated] = useState(false);
  const [syncTable, setSyncTable] = useState(false);

  const numberFormatter = useMemo(
    () => new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }),
    []
  );

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

  const handleValidate = async (event) => {
    event.preventDefault();
    setValidationError(null);

    const trimmedUserId = filters.userId.trim();
    if (!trimmedUserId) {
      setValidationError("Please enter a user ID.");
      return;
    }

    const amountValue = parseFloat(filters.amount);
    if (!Number.isFinite(amountValue)) {
      setValidationError("Please enter a numeric amount.");
      return;
    }

    setHasValidated(true);
    setValidating(true);
    try {
      const payload = {
        user_id: trimmedUserId,
        amount: amountValue,
      };
      const locationValue = filters.location.trim();
      if (locationValue) {
        payload.location = locationValue;
      }

      const res = await axios.post(
        "http://127.0.0.1:5000/validate-transaction",
        payload
      );
      setValidationResult(res.data);
    } catch (err) {
      const message =
        err.response?.data?.error ||
        err.message ||
        "Unable to validate transaction.";
      setValidationError(message);
      setValidationResult((prev) => prev);
    } finally {
      setValidating(false);
    }
  };

  const handleReset = () => {
    const reset = { userId: "", amount: "", location: "" };
    setFilters(reset);
    setAppliedFilters(reset);
    setValidationResult(null);
    setValidationError(null);
    setShowAdvanced(false);
    setHasValidated(false);
    setSyncTable(false);
  };

  const handleSyncChange = (event) => {
    const { checked } = event.target;
    setSyncTable(checked);
    if (!checked) {
      setAppliedFilters({ userId: "", amount: "", location: "" });
    }
  };

  const activeFilters = useMemo(() => {
    if (syncTable) {
      return {
        userId: filters.userId,
        amount: filters.amount,
        location: filters.location,
      };
    }
    return appliedFilters;
  }, [syncTable, filters, appliedFilters]);

  const filteredTransactions = useMemo(() => {
    if (!activeFilters.userId && !activeFilters.amount) {
      return transactions;
    }

    const userIdQuery = activeFilters.userId.trim().toLowerCase();
    const amountThreshold = parseFloat(activeFilters.amount);

    return transactions.filter((tx) => {
      const userId = (tx.user_id ?? tx.userId ?? "").toString().toLowerCase();
      const amount = parseFloat(tx.amount);

      const matchesUser = userIdQuery ? userId.includes(userIdQuery) : true;
      const matchesAmount = Number.isFinite(amountThreshold)
        ? Number.isFinite(amount) && amount >= amountThreshold
        : true;

      return matchesUser && matchesAmount;
    });
  }, [transactions, activeFilters]);

  const total = stats.total ?? transactions.length;
  const fraudCount = stats.frauds ?? 0;
  const fraudPercent = total > 0 ? ((fraudCount / total) * 100).toFixed(1) : 0;
  const validCount = Math.max(total - fraudCount, 0);

  const statCards = useMemo(() => {
    const safeTotal = Number.isFinite(Number(total)) ? Number(total) : 0;
    const safeFraud = Number.isFinite(Number(fraudCount)) ? Number(fraudCount) : 0;
    const safeValid = Number.isFinite(Number(validCount)) ? Number(validCount) : 0;
    const rateNumber = Number(fraudPercent);
    const formattedRate = Number.isFinite(rateNumber)
      ? `${rateNumber.toFixed(1)}%`
      : "0%";

    return [
      {
        label: "Total Transactions",
        value: numberFormatter.format(Math.max(safeTotal, 0)),
        tone: "blue",
        badge: "TX",
      },
      {
        label: "Detected Frauds",
        value: numberFormatter.format(Math.max(safeFraud, 0)),
        tone: "red",
        badge: "FR",
      },
      {
        label: "Valid Transactions",
        value: numberFormatter.format(Math.max(safeValid, 0)),
        tone: "green",
        badge: "OK",
      },
      {
        label: "Fraud Rate",
        value: formattedRate,
        tone: "amber",
        badge: "%",
      },
    ];
  }, [fraudCount, fraudPercent, numberFormatter, total, validCount]);

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

  const validationStatus = validationResult?.status === "fraud" ? "fraud" : "valid";
  const validationFlags = validationResult?.flag_details || [];
  const validationHistory = validationResult?.history || {};
  const validationEvaluated = validationResult?.evaluated || {};
  const showValidationSkeleton = validating && !validationResult && !validationError;

  return (
    <div className="container">
      <div className="header">
        <div className="header-titles">
          <h1 className="title">Fraud Detection Dashboard</h1>
          <p className="subtitle">Real-time oversight for payments risk and anomaly monitoring.</p>
        </div>
        <div className="status-bar" role="status" aria-live="polite">
          <span className="live-dot"></span>
          <div className="status-copy">
            <span className="status-label">Live</span>
            <span className="status-hint">{refreshing ? "Refreshing data" : "Stream healthy"}</span>
          </div>
          {refreshing && <span className="refresh" aria-hidden="true">⟳</span>}
        </div>
      </div>

      <div className="dashboard-top">
        <div className="left-column">
          <div className="stat-card-grid">
            {statCards.map((card) => (
              <StatCard key={card.label} {...card} />
            ))}
          </div>

          <div className="form-card panel">
            <h3 className="section-title">Transaction Lookup</h3>
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
                {showAdvanced && (
                  <div className="input-group">
                    <label htmlFor="location">Location (optional)</label>
                    <input
                      id="location"
                      name="location"
                      placeholder="Enter location"
                      value={filters.location}
                      onChange={handleInputChange}
                    />
                  </div>
                )}
              </div>
              <div className="form-controls-row">
                <button
                  type="button"
                  className="advanced-toggle"
                  onClick={() => setShowAdvanced((prev) => !prev)}
                >
                  {showAdvanced ? "Hide advanced fields" : "Add location (optional)"}
                </button>
                <label className="form-toggle">
                  <input
                    type="checkbox"
                    checked={syncTable}
                    onChange={handleSyncChange}
                  />
                  <span className="toggle-indicator" aria-hidden="true"></span>
                  <span className="toggle-label">Sync table results</span>
                </label>
              </div>
              <div className="actions button-row">
                <button type="submit" className="primary-btn" disabled={validating}>
                  {validating ? "Checking..." : "Validate"}
                </button>
                <button type="button" className="secondary-btn" onClick={handleReset}>
                  Reset
                </button>
              </div>
            </form>
            <div className={`validation-section${hasValidated ? " active" : ""}`}>
              {showValidationSkeleton && (
                <div className="validation-banner pending">
                  <div className="validation-header">
                    <span className="status-pill pending">Checking</span>
                    <span className="validation-context">Running rule heuristics and anomaly score...</span>
                  </div>
                  <p className="validation-safe">Hold tight — we’ll surface a verdict in a second.</p>
                </div>
              )}
              {validationError && (
                <div className="validation-banner error">
                  <span>{validationError}</span>
                </div>
              )}
              {validationResult && (
                <div className={`validation-banner ${validationStatus}`}>
                  <div className="validation-header">
                    <span className={`status-pill ${validationStatus}`}>
                      {validationStatus === "fraud" ? "Fraud" : "Valid"}
                    </span>
                    <span className="validation-context">
                      Amount {formatAmount(validationEvaluated.amount)}
                      {validationHistory.average_amount != null
                        ? ` · Avg ${formatAmount(validationHistory.average_amount)}`
                        : ""}
                    </span>
                  </div>
                  {validationHistory.recent_count ? (
                    <div className="validation-meta">
                      Last txn {formatTime(validationHistory.last_time)}
                      {validationHistory.last_location
                        ? ` · ${validationHistory.last_location}`
                        : ""}
                    </div>
                  ) : (
                    <div className="validation-meta">No prior history for this user.</div>
                  )}
                  {validationFlags.length > 0 ? (
                    <ul className="validation-flags">
                      {validationFlags.map((flag) => (
                        <li key={flag.code}>
                          <strong>{flag.code}</strong>: {flag.message}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="validation-safe">No fraud rules fired for this scenario.</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="chart-card panel">
          <h3 className="section-title">Transaction Distribution</h3>
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
        <div className={`table-wrapper panel ${refreshing ? "dim" : ""}`}>
          <div className="table-scroll">
            <table className="data-table">
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
                const reason = tx.fraud_reason ?? tx.reason ?? tx.flags;
                const statusClass = status === "Fraud" ? "status-pill fraud" : "status-pill valid";

                return (
                  <tr key={transactionId !== "—" ? transactionId : `row-${id}-${idx}`}>
                    <td>{id}</td>
                    <td>{transactionId}</td>
                    <td>{userId}</td>
                    <td>{formatAmount(amount)}</td>
                    <td>{formatTime(time)}</td>
                    <td>
                      <span className={statusClass} title={reason ? `Reason: ${reason}` : undefined}>
                        {status}
                      </span>
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
        </div>
      )}
    </div>
  );
}

export default App;
