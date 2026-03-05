class ProductNotFoundError(Exception):
    pass


class InsufficientStockError(Exception):
    pass

from datetime import datetime
from repository import (
    get_product_by_id,
    insert_invoice,
    insert_invoice_item,
    reduce_product_stock
)


def create_invoice_service(cursor, invoice):
    subtotal = 0

    # Phase 1: Validate + Calculate
    for item in invoice.items:
        product = get_product_by_id(cursor, item.product_id)

        if not product:
            raise ProductNotFoundError(f"Product {item.product_id} not found")

        if product["stock_quantity"] < item.quantity:
            raise InsufficientStockError(f"Insufficient stock for {product['name']}")

        subtotal += product["current_price"] * item.quantity

    tax = round(subtotal * 0.18, 2)
    total = round(subtotal + tax, 2)

    invoice_number = f"INV-{int(datetime.now().timestamp())}"

    # Phase 2: Insert invoice
    invoice_id = insert_invoice(
        cursor,
        invoice_number,
        invoice.customer_name,
        subtotal,
        tax,
        total
    )

    # Phase 3: Insert items + reduce stock
    for item in invoice.items:
        product = get_product_by_id(cursor, item.product_id)

        line_total = product["current_price"] * item.quantity

        insert_invoice_item(
            cursor,
            invoice_id,
            item.product_id,
            item.quantity,
            product["current_price"],
            line_total
        )

        reduce_product_stock(
            cursor,
            item.product_id,
            item.quantity
        )

    return invoice_id, invoice_number, total

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