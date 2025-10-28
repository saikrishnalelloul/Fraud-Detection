# quick python check
import sqlite3
conn = sqlite3.connect('transactions.db')
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM transactions")
print(cur.fetchone())
conn.close()