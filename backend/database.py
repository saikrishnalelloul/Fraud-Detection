import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().with_name("transactions.db")
DB_PATH = Path(os.getenv("TRANSACTIONS_DB_PATH", DEFAULT_DB_PATH))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Function to get connection (always opens fresh)
def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            location TEXT,
            device TEXT,
            time TEXT,
            timestamp TEXT,
            prediction TEXT,
            is_fraud INTEGER,
            risk_score REAL,
            fraud_reason TEXT
        )
        """
    )
    conn.commit()
    return conn, cursor

# Function to insert a transaction
def insert_transaction(transaction, prediction=None):
    conn, cursor = get_connection()
    payload = {
        "transaction_id": transaction.get("transaction_id"),
        "user_id": transaction.get("user_id"),
        "amount": transaction.get("amount"),
        "location": transaction.get("location"),
        "device": transaction.get("device"),
        "time": transaction.get("time"),
        "timestamp": transaction.get("timestamp") or transaction.get("time"),
        "prediction": prediction,
        "is_fraud": transaction.get("is_fraud"),
        "risk_score": transaction.get("risk_score"),
        "fraud_reason": transaction.get("fraud_reason"),
    }
    cursor.execute(
        """
        INSERT INTO transactions (
            transaction_id,
            user_id,
            amount,
            location,
            device,
            time,
            timestamp,
            prediction,
            is_fraud,
            risk_score,
            fraud_reason
        )
        VALUES (
            :transaction_id,
            :user_id,
            :amount,
            :location,
            :device,
            :time,
            :timestamp,
            :prediction,
            :is_fraud,
            :risk_score,
            :fraud_reason
        )
        ON CONFLICT(transaction_id) DO UPDATE SET
            user_id=excluded.user_id,
            amount=excluded.amount,
            location=excluded.location,
            device=excluded.device,
            time=excluded.time,
            timestamp=excluded.timestamp,
            prediction=excluded.prediction,
            is_fraud=excluded.is_fraud,
            risk_score=excluded.risk_score,
            fraud_reason=excluded.fraud_reason
        """,
        payload,
    )
    conn.commit()
    conn.close()


def fetch_recent_transactions_by_user(user_id, limit=5):
    if user_id is None:
        return []
    conn, cursor = get_connection()
    try:
        cursor.execute(
            """
            SELECT rowid AS sqlite_rowid, *
            FROM transactions
            WHERE user_id = ?
            ORDER BY datetime(COALESCE(timestamp, time)) DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
