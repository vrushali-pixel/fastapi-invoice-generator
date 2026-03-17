from database import get_connection

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ─────────────────────────────────────────
    # CONCEPT: PostgreSQL vs SQLite differences
    #
    # 1. SERIAL instead of INTEGER AUTOINCREMENT
    #    SQLite:     id INTEGER PRIMARY KEY AUTOINCREMENT
    #    PostgreSQL: id SERIAL PRIMARY KEY
    #
    # 2. TIMESTAMP WITH TIME ZONE instead of TIMESTAMP
    #    PostgreSQL is timezone-aware — good practice
    #    for production apps used across timezones.
    #
    # 3. TEXT instead of TEXT NOT NULL where appropriate
    #    PostgreSQL enforces constraints more strictly.
    #
    # 4. IF NOT EXISTS still works — safe to run multiple times.
    # ─────────────────────────────────────────

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        current_price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id SERIAL PRIMARY KEY,
        invoice_number TEXT UNIQUE,
        customer_name TEXT NOT NULL,
        subtotal REAL,
        tax REAL,
        total REAL,
        pdf_path TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoice_items (
        id SERIAL PRIMARY KEY,
        invoice_id INTEGER REFERENCES invoices(id),
        product_id INTEGER REFERENCES products(id),
        quantity INTEGER,
        unit_price REAL,
        line_total REAL
    )
    """)

    # ─────────────────────────────────────────
    # CONCEPT: Indexes
    # An index is like the index at the back of a book.
    # Without index: PostgreSQL reads EVERY row to find email="x"
    # With index:    PostgreSQL jumps directly to that row.
    # We index email and invoice_number because we
    # query by them frequently.
    # ─────────────────────────────────────────
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_users_email 
    ON users(email)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_invoices_number 
    ON invoices(invoice_number)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_invoices_created 
    ON invoices(created_at)
    """)

    conn.commit()
    conn.close()
    print("PostgreSQL tables and indexes created successfully.")