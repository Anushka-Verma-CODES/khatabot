import sqlite3

def get_db():
    conn = sqlite3.connect("khatabot.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            channel TEXT DEFAULT 'whatsapp' CHECK(channel IN ('whatsapp', 'sms')),
            credit_limit_paise INTEGER DEFAULT 200000,
            opening_balance_paise INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
            amount_paise INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('credit', 'payment')),
            note TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
            message TEXT,
            status TEXT DEFAULT 'open' CHECK(status IN ('open', 'resolved')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

def get_balance(customer_id):
    """Returns current balance in paise: opening + credits - payments"""
    conn = get_db()
    row = conn.execute('''
        SELECT
            c.opening_balance_paise,
            COALESCE(SUM(CASE WHEN t.type = 'credit' THEN t.amount_paise ELSE 0 END), 0) AS total_credit,
            COALESCE(SUM(CASE WHEN t.type = 'payment' THEN t.amount_paise ELSE 0 END), 0) AS total_payment
        FROM customers c
        LEFT JOIN transactions t ON t.customer_id = c.id
        WHERE c.id = ?
        GROUP BY c.id
    ''', (customer_id,)).fetchone()
    conn.close()
    if not row:
        return 0
    return row['opening_balance_paise'] + row['total_credit'] - row['total_payment']
