import os
import sqlite3
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().with_name("transactions.db")
DB_PATH = Path(os.getenv("TRANSACTIONS_DB_PATH", DEFAULT_PATH))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

CREATE_SQL = """
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
    risk_score REAL
);
"""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(CREATE_SQL)
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("db initialized:", DB_PATH)