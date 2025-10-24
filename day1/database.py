import sqlite3

# Function to get connection (always opens fresh)
def get_connection():
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()
    # Create table if not exists
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY,
        amount REAL,
        location TEXT,
        device TEXT,
        time TEXT,
        prediction TEXT
    )
    ''')
    conn.commit()
    return conn, cursor

# Function to insert a transaction
def insert_transaction(transaction, prediction):
    conn, cursor = get_connection()
    cursor.execute('''
        INSERT OR REPLACE INTO transactions
        (transaction_id, amount, location, device, time, prediction)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        transaction['transaction_id'],
        transaction['amount'],
        transaction['location'],
        transaction['device'],
        transaction['time'],
        prediction
    ))
    conn.commit()
    conn.close()
