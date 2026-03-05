def get_product_by_id(cursor, product_id: int):
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    return cursor.fetchone()
def insert_invoice(cursor, invoice_number, customer_name, subtotal, tax, total):
    cursor.execute("""
        INSERT INTO invoices (invoice_number, customer_name, subtotal, tax, total)
        VALUES (?, ?, ?, ?, ?)
    """, (invoice_number, customer_name, subtotal, tax, total))

    return cursor.lastrowid
def insert_invoice_item(cursor, invoice_id, product_id, quantity, unit_price, line_total):
    cursor.execute("""
        INSERT INTO invoice_items 
        (invoice_id, product_id, quantity, unit_price, line_total)
        VALUES (?, ?, ?, ?, ?)
    """, (invoice_id, product_id, quantity, unit_price, line_total))


def reduce_product_stock(cursor, product_id, quantity):
    cursor.execute("""
        UPDATE products
        SET stock_quantity = stock_quantity - ?
        WHERE id = ?
    """, (quantity, product_id))

def get_invoice_by_id(cursor, invoice_id: int):
    cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    return cursor.fetchone()


def get_invoice_items(cursor, invoice_id: int):
    cursor.execute("""
        SELECT ii.*, p.name 
        FROM invoice_items ii
        JOIN products p ON ii.product_id = p.id
        WHERE ii.invoice_id = ?
    """, (invoice_id,))
    return cursor.fetchall()