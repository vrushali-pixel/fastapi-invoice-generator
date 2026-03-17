# ─────────────────────────────────────────────
# CONCEPT: PostgreSQL uses %s for placeholders
# SQLite used ? for query parameters.
# PostgreSQL uses %s instead.
# Both prevent SQL injection — never use f-strings
# or string concatenation for SQL queries.
#
# WRONG:  f"SELECT * FROM products WHERE id = {product_id}"
# RIGHT:  "SELECT * FROM products WHERE id = %s", (product_id,)
# ─────────────────────────────────────────────

def get_product_by_id(cursor, product_id: int):
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    return cursor.fetchone()


def insert_invoice(cursor, invoice_number, customer_name, subtotal, tax, total):
    # CONCEPT: RETURNING id
    # PostgreSQL can return the inserted row's id immediately.
    # SQLite used cursor.lastrowid — PostgreSQL uses RETURNING.
    cursor.execute("""
        INSERT INTO invoices (invoice_number, customer_name, subtotal, tax, total)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (invoice_number, customer_name, subtotal, tax, total))
    return cursor.fetchone()["id"]


def insert_invoice_item(cursor, invoice_id, product_id, quantity, unit_price, line_total):
    cursor.execute("""
        INSERT INTO invoice_items 
        (invoice_id, product_id, quantity, unit_price, line_total)
        VALUES (%s, %s, %s, %s, %s)
    """, (invoice_id, product_id, quantity, unit_price, line_total))


def reduce_product_stock(cursor, product_id, quantity):
    cursor.execute("""
        UPDATE products
        SET stock_quantity = stock_quantity - %s
        WHERE id = %s
    """, (quantity, product_id))


def get_invoice_by_id(cursor, invoice_id: int):
    cursor.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
    return cursor.fetchone()


def get_invoice_items(cursor, invoice_id: int):
    cursor.execute("""
        SELECT ii.*, p.name 
        FROM invoice_items ii
        JOIN products p ON ii.product_id = p.id
        WHERE ii.invoice_id = %s
    """, (invoice_id,))
    return cursor.fetchall()