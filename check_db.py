import sqlite3
conn = sqlite3.connect('khatabot.db')
conn.row_factory = sqlite3.Row
customers = conn.execute("SELECT * FROM customers").fetchall()
for c in customers:
    print(c['name'], c['phone'], c['channel'], c['balance'])
conn.close()