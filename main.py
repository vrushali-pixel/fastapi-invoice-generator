from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
import os

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from init_db import init_db
from database import get_connection
from security import verify_api_key
from schemas import ProductCreate, InvoiceCreate
from repository import get_invoice_by_id, get_invoice_items
from repository import (
    get_product_by_id,
    insert_invoice,
    insert_invoice_item,
    reduce_product_stock,
)
from service import (
    create_invoice_service,
    ProductNotFoundError,
    InsufficientStockError,
)
from auth_router import router as auth_router
from jwt_dependency import get_current_user
from tasks import generate_pdf_task

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas

# CONCEPT: Rate Limiting with slowapi
# Limiter tracks requests per IP address.
# @limiter.limit("10/minute") means that IP
# can only call it 10 times per minute.
# On the 11th call -> 429 Too Many Requests.
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database initialised.")
    yield
    print("App shutting down.")


app = FastAPI(
    title="Invoice Generator API",
    description="Production-grade invoice management with async PDF generation.",
    version="1.0.0",
    lifespan=lifespan,
)

# Attach limiter to app
# add_exception_handler returns clean 429 response automatically
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(auth_router)

PDF_FOLDER = "pdfs"
os.makedirs(PDF_FOLDER, exist_ok=True)


@app.get("/")
def root():
    return {"message": "Invoice Generator API is running."}


@app.get("/health")
def health_check():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=500, detail="Database connection failed")


@app.post("/products", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
def create_product(request: Request, product: ProductCreate):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, current_price, stock_quantity) VALUES (%s, %s, %s)",
        (product.name, product.current_price, product.stock_quantity),
    )
    conn.commit()
    conn.close()
    return {"message": "Product created successfully"}


@app.get("/products", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/minute")
def get_products(request: Request):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/invoices", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
def create_invoice(request: Request, invoice: InvoiceCreate):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        invoice_id, invoice_number, total = create_invoice_service(cursor, invoice)
        conn.commit()
    except ProductNotFoundError as e:
        conn.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except InsufficientStockError as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "message": "Invoice created successfully",
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        "total": total,
    }


@app.get("/invoices", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/minute")
def get_all_invoices(request: Request):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/invoices/stats/summary", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
def invoice_stats(request: Request):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) as total FROM invoices")
        total = cursor.fetchone()["total"]
        cursor.execute("SELECT COALESCE(SUM(total), 0) as revenue FROM invoices")
        revenue = cursor.fetchone()["revenue"]
        cursor.execute("SELECT COUNT(*) as today FROM invoices WHERE created_at::date = CURRENT_DATE")
        today = cursor.fetchone()["today"]
        cursor.execute("SELECT COUNT(*) as total_products FROM products")
        total_products = cursor.fetchone()["total_products"]
        return {
            "total_invoices": total,
            "total_revenue": round(revenue, 2),
            "invoices_today": today,
            "total_products": total_products,
        }
    finally:
        conn.close()


@app.get("/invoices/{invoice_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/minute")
def get_invoice(request: Request, invoice_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        invoice = get_invoice_by_id(cursor, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        items = get_invoice_items(cursor, invoice_id)
        return {
            "invoice": dict(invoice),
            "items": [dict(item) for item in items],
        }
    finally:
        conn.close()


@app.post("/invoices/{invoice_id}/pdf", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
def generate_invoice_pdf(request: Request, invoice_id: int, template: str = "standard"):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        invoice = get_invoice_by_id(cursor, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
    finally:
        conn.close()

    task = generate_pdf_task.delay(invoice_id, template)

    return {
        "message": "PDF generation started",
        "task_id": task.id,
        "status_url": f"/tasks/{task.id}",
        "template": template,
    }


@app.get("/tasks/{task_id}", dependencies=[Depends(verify_api_key)])
@limiter.limit("60/minute")
def get_task_status(request: Request, task_id: str):
    result = generate_pdf_task.AsyncResult(task_id)
    if result.state == "PENDING":
        return {"task_id": task_id, "status": "pending"}
    elif result.state == "STARTED":
        return {"task_id": task_id, "status": "processing"}
    elif result.state == "SUCCESS":
        return {"task_id": task_id, "status": "completed", "result": result.result}
    elif result.state == "FAILURE":
        return {"task_id": task_id, "status": "failed", "error": str(result.result)}
    else:
        return {"task_id": task_id, "status": result.state}


@app.get("/invoices/{invoice_id}/pdf/download", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
def download_invoice_pdf(request: Request, invoice_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        invoice = get_invoice_by_id(cursor, invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if not invoice["pdf_path"] or not os.path.exists(invoice["pdf_path"]):
            raise HTTPException(
                status_code=404,
                detail="PDF not generated yet. POST to /invoices/{id}/pdf first."
            )
        return FileResponse(
            invoice["pdf_path"],
            media_type="application/pdf",
            filename=f"{invoice['invoice_number']}.pdf",
        )
    finally:
        conn.close()


def _draw_invoice_header(c, invoice, width, y):
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
    y = _draw_invoice_header(c, invoice, width, y)
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
    y = _draw_invoice_header(c, invoice, width, y)
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
    y = _draw_invoice_header(c, invoice, width, y)
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