import sqlite3
from pathlib import Path

DB_PATH = Path("transactions.db")  # adjust if your app uses a different path

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    timestamp TEXT NOT NULL,
    is_fraud INTEGER NOT NULL,
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