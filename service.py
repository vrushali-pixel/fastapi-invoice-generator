# CONCEPT: Custom exceptions
# We define our own exception classes instead of using
# generic ValueError or Exception.
# Why? Because the route layer can catch SPECIFIC errors
# and return the correct HTTP status code for each.
# ProductNotFoundError → 404
# InsufficientStockError → 400
# Any other Exception → 500 (unhandled, let it crash loudly)

class ProductNotFoundError(Exception):
    pass


class InsufficientStockError(Exception):
    pass


from datetime import datetime
from repository import (
    get_product_by_id,
    insert_invoice,
    insert_invoice_item,
    reduce_product_stock,
)


def create_invoice_service(cursor, invoice):
    """
    Orchestrates invoice creation in 3 phases.

    Phase 1: Validate ALL items before touching the database.
             If anything is wrong, we raise immediately.
             No partial writes.

    Phase 2: Insert the invoice header (customer, totals).

    Phase 3: Insert each line item and deduct stock.

    The cursor is passed in from the route layer, which
    controls the transaction (commit/rollback lives there).
    This keeps the service layer pure business logic —
    it never commits or rolls back directly.
    """

    # ── Phase 1: Validate + calculate ──────────────
    subtotal = 0
    validated_items = []

    for item in invoice.items:
        product = get_product_by_id(cursor, item.product_id)

        if not product:
            raise ProductNotFoundError(f"Product {item.product_id} not found")

        if product["stock_quantity"] < item.quantity:
            raise InsufficientStockError(
                f"Insufficient stock for '{product['name']}'. "
                f"Requested: {item.quantity}, Available: {product['stock_quantity']}"
            )

        line_total = product["current_price"] * item.quantity
        subtotal += line_total

        # Cache validated product data so Phase 3 doesn't re-query
        validated_items.append({
            "product_id": item.product_id,
            "product_name": product["name"],
            "quantity": item.quantity,
            "unit_price": product["current_price"],
            "line_total": line_total,
        })

    tax = round(subtotal * 0.18, 2)
    total = round(subtotal + tax, 2)
    invoice_number = f"INV-{int(datetime.now().timestamp())}"

    # ── Phase 2: Insert invoice header ─────────────
    invoice_id = insert_invoice(
        cursor,
        invoice_number,
        invoice.customer_name,
        subtotal,
        tax,
        total,
    )

    # ── Phase 3: Insert items + reduce stock ────────
    for item_data in validated_items:
        insert_invoice_item(
            cursor,
            invoice_id,
            item_data["product_id"],
            item_data["quantity"],
            item_data["unit_price"],
            item_data["line_total"],
        )
        reduce_product_stock(cursor, item_data["product_id"], item_data["quantity"])

    return invoice_id, invoice_number, total
