from celery_app import celery
from database import get_connection
from repository import get_invoice_by_id, get_invoice_items
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas
import os

PDF_FOLDER = "pdfs"
os.makedirs(PDF_FOLDER, exist_ok=True)


# ─────────────────────────────────────────────
# CONCEPT: @celery_app.task decorator
# This turns a normal Python function into a
# Celery task. When you call .delay() on it,
# instead of running immediately, it sends a
# message to Redis saying "run this function
# with these arguments".
# A Celery worker process picks it up and runs it.
#
# Key point: the API process and the worker process
# are SEPARATE. The API returns immediately.
# The worker runs in the background.
# ─────────────────────────────────────────────

@celery.task(bind=True)
def generate_pdf_task(self, invoice_id: int, template: str = "standard"):
    """
    Background task to generate invoice PDF.

    'bind=True' means 'self' is the task instance.
    This lets us update task progress and handle retries.

    States this task goes through:
    PENDING → STARTED → SUCCESS (or FAILURE)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        invoice = get_invoice_by_id(cursor, invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        items = get_invoice_items(cursor, invoice_id)
        file_path = os.path.join(PDF_FOLDER, f"{invoice['invoice_number']}.pdf")

        if template == "minimal":
            _generate_minimal_pdf(file_path, invoice, items)
        elif template == "detailed":
            _generate_detailed_pdf(file_path, invoice, items)
        else:
            _generate_standard_pdf(file_path, invoice, items)

        cursor.execute(
            "UPDATE invoices SET pdf_path = %s WHERE id = %s",
            (file_path, invoice_id),
        )
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "invoice_id": invoice_id,
            "file_path": file_path,
            "template": template,
        }

    except Exception as exc:
        # ─────────────────────────────────────
        # CONCEPT: Retry logic
        # If task fails, retry up to 3 times.
        # Wait 5 seconds before each retry.
        # This handles temporary failures like
        # DB connection drops or file system issues.
        # After 3 retries, task is marked FAILURE.
        # ─────────────────────────────────────
        raise self.retry(exc=exc, countdown=5, max_retries=3)


def _draw_header(c, invoice, y):
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "INVOICE")
    c.setFont("Helvetica", 10)
    c.drawString(50, y - 20, f"Invoice Number: {invoice['invoice_number']}")
    c.drawString(50, y - 35, f"Customer: {invoice['customer_name']}")
    c.drawString(50, y - 50, f"Date: {invoice['created_at']}")
    return y - 80


def _generate_standard_pdf(file_path, invoice, items):
    c = pdf_canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    y = height - 50
    y = _draw_header(c, invoice, y)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Product")
    c.drawString(280, y, "Qty")
    c.drawString(340, y, "Unit Price")
    c.drawString(440, y, "Line Total")
    y -= 5
    c.line(50, y, 550, y)
    y -= 15
    c.setFont("Helvetica", 10)
    for item in items:
        c.drawString(50, y, str(item["name"]))
        c.drawString(280, y, str(item["quantity"]))
        c.drawString(340, y, f"Rs. {item['unit_price']:.2f}")
        c.drawString(440, y, f"Rs. {item['line_total']:.2f}")
        y -= 18
    y -= 10
    c.line(50, y, 550, y)
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(380, y, f"Subtotal: Rs. {invoice['subtotal']:.2f}")
    y -= 15
    c.drawString(380, y, f"Tax (18%): Rs. {invoice['tax']:.2f}")
    y -= 15
    c.setFont("Helvetica-Bold", 11)
    c.drawString(380, y, f"Total: Rs. {invoice['total']:.2f}")
    c.save()


def _generate_minimal_pdf(file_path, invoice, items):
    c = pdf_canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    y = height - 50
    y = _draw_header(c, invoice, y)
    c.setFont("Helvetica", 10)
    for item in items:
        c.drawString(50, y, f"- {item['name']}  x{item['quantity']}  Rs. {item['line_total']:.2f}")
        y -= 16
    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, f"Total (incl. 18% tax): Rs. {invoice['total']:.2f}")
    c.save()


def _generate_detailed_pdf(file_path, invoice, items):
    c = pdf_canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    y = height - 50
    y = _draw_header(c, invoice, y)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Product")
    c.drawString(240, y, "Qty")
    c.drawString(290, y, "Unit Price")
    c.drawString(380, y, "Item Tax")
    c.drawString(460, y, "Line Total")
    y -= 5
    c.line(50, y, 560, y)
    y -= 15
    c.setFont("Helvetica", 9)
    for item in items:
        item_tax = round(item["line_total"] * 0.18, 2)
        c.drawString(50, y, str(item["name"]))
        c.drawString(240, y, str(item["quantity"]))
        c.drawString(290, y, f"Rs. {item['unit_price']:.2f}")
        c.drawString(380, y, f"Rs. {item_tax:.2f}")
        c.drawString(460, y, f"Rs. {item['line_total']:.2f}")
        y -= 18
    y -= 10
    c.line(50, y, 560, y)
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(380, y, f"Subtotal: Rs. {invoice['subtotal']:.2f}")
    y -= 15
    c.drawString(380, y, f"GST (18%): Rs. {invoice['tax']:.2f}")
    y -= 15
    c.setFont("Helvetica-Bold", 11)
    c.drawString(380, y, f"Grand Total: Rs. {invoice['total']:.2f}")
    c.save()