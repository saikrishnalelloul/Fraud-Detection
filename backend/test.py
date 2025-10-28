from database import insert_transaction

# Sample transaction
sample_txn = {
    'transaction_id': 'TXN001',
    'amount': 500,
    'location': 'Hyderabad',
    'device': 'Mobile',
    'time': '2025-10-24 17:00:00'
}

# Insert into database
insert_transaction(sample_txn, 'normal')

# Check DB
import sqlite3
conn = sqlite3.connect('transactions.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM transactions")
rows = cursor.fetchall()
print(rows)
conn.close()
