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
        CREATE TABLE IF NOT EXISTS merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id INTEGER NOT NULL REFERENCES merchants(id) ON DELETE RESTRICT,
            name TEXT NOT NULL,
            address TEXT,
            whatsapp_number TEXT UNIQUE,
            sms_sender_id TEXT,
            default_credit_limit_paise INTEGER DEFAULT 200000,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # phone is the only global truth about a customer
    # name is NOT here — it belongs to the merchant relationship
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # name lives here — each merchant stores their own version
    # Ramesh at shop A, Ramesh Kumar at shop B — same phone, different names
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_customer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL REFERENCES shops(id) ON DELETE RESTRICT,
            customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
            name TEXT NOT NULL,
            channel TEXT DEFAULT 'sms' CHECK(channel IN ('sms', 'whatsapp')),
            credit_limit_paise INTEGER DEFAULT 200000,
            opening_balance_paise INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(shop_id, customer_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_customer_id INTEGER NOT NULL REFERENCES shop_customer(id) ON DELETE RESTRICT,
            amount_paise INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('credit', 'payment')),
            note TEXT,
            logged_by TEXT DEFAULT 'dashboard',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_customer_id INTEGER REFERENCES shop_customer(id) ON DELETE SET NULL,
            message TEXT,
            status TEXT DEFAULT 'open' CHECK(status IN ('open', 'resolved')),
            replied_text TEXT,
            resolved_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_customer_id INTEGER REFERENCES shop_customer(id) ON DELETE SET NULL,
            channel TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'sent' CHECK(status IN ('sent', 'failed', 'retried')),
            error_detail TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def get_balance(shop_customer_id: int) -> int:
    """
    Returns current balance in paise for a specific shop_customer record.
    balance = opening_balance + sum(credits) - sum(payments)
    """
    conn = get_db()
    row = conn.execute('''
        SELECT
            sc.opening_balance_paise,
            COALESCE(SUM(CASE WHEN t.type = 'credit' THEN t.amount_paise ELSE 0 END), 0) AS total_credit,
            COALESCE(SUM(CASE WHEN t.type = 'payment' THEN t.amount_paise ELSE 0 END), 0) AS total_payment
        FROM shop_customer sc
        LEFT JOIN transactions t ON t.shop_customer_id = sc.id
        WHERE sc.id = ?
        GROUP BY sc.id
    ''', (shop_customer_id,)).fetchone()
    conn.close()
    if not row:
        return 0
    return row['opening_balance_paise'] + row['total_credit'] - row['total_payment']


def get_or_create_customer(phone: str) -> int:
    """
    Looks up a customer by phone. Creates one if not found.
    Returns the customer id.
    This is the only place a global customer row is created.
    Name is NOT set here — it lives on shop_customer.
    """
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM customers WHERE phone = ?", (phone,)
    ).fetchone()
    if row:
        conn.close()
        return row["id"]
    cursor = conn.execute(
        "INSERT INTO customers (phone) VALUES (?)", (phone,)
    )
    conn.commit()
    customer_id = cursor.lastrowid
    conn.close()
    return customer_id


def get_shop_customer(shop_id: int, customer_id: int):
    """Returns the shop_customer row for a given shop + customer pair."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM shop_customer WHERE shop_id = ? AND customer_id = ?",
        (shop_id, customer_id)
    ).fetchone()
    conn.close()
    return row


def get_shop_customer_by_phone(shop_id: int, phone: str):
    """
    Looks up a shop_customer record by shop + customer phone.
    Used in webhook routing and dashboard lookups.
    """
    conn = get_db()
    row = conn.execute('''
        SELECT sc.*, c.phone
        FROM shop_customer sc
        JOIN customers c ON c.id = sc.customer_id
        WHERE sc.shop_id = ? AND c.phone = ?
    ''', (shop_id, phone)).fetchone()
    conn.close()
    return row