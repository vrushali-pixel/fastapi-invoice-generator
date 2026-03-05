from security import verify_api_key
from fastapi import Depends
from repository import get_invoice_by_id, get_invoice_items
from repository import (
    get_product_by_id,
    insert_invoice,
    insert_invoice_item,
    reduce_product_stock
)
from repository import get_product_by_id
from schemas import ProductCreate, InvoiceCreate
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
import os

from init_db import init_db
from database import get_connection

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ================= LIFESPAN =================
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    print("App shutting down...")

app = FastAPI(lifespan=lifespan)

# ================= PDF FOLDER SETUP =================
PDF_FOLDER = "pdfs"

if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)

# ================= ROOT =================
@app.get("/")
def root():
    return {"message": "Invoice Generator API running"}

# ================= PRODUCT MODELS =================
class ProductCreate(BaseModel):
    name: str
    current_price: float = Field(..., gt=0)
    stock_quantity: int = Field(..., ge=0)

# ================= INVOICE MODELS =================
class InvoiceItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)

class InvoiceCreate(BaseModel):
    customer_name: str
    items: List[InvoiceItemCreate]

# ================= PRODUCT ENDPOINTS =================
@app.post("/products")
def create_product(product: ProductCreate):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO products (name, current_price, stock_quantity)
        VALUES (?, ?, ?)
        """,
        (product.name, product.current_price, product.stock_quantity)
    )

    conn.commit()
    conn.close()

    return {"message": "Product created successfully"}

@app.get("/products")
def get_products():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM products")
    rows = cursor.fetchall()

    products = [dict(row) for row in rows]

    conn.close()
    return products

# ================= CREATE INVOICE =================
from service import (
    create_invoice_service,
    ProductNotFoundError,
    InsufficientStockError
)

@app.post("/invoices")
def create_invoice(invoice: InvoiceCreate):
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
        "total": total
    }

# ================= GENERATE PDF =================
@app.post("/invoices/{invoice_id}/pdf")
def generate_invoice_pdf(invoice_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    invoice = cursor.fetchone()

    if not invoice:
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")

    cursor.execute("""
        SELECT ii.*, p.name 
        FROM invoice_items ii
        JOIN products p ON ii.product_id = p.id
        WHERE ii.invoice_id = ?
    """, (invoice_id,))
    items = cursor.fetchall()

    file_path = os.path.join(PDF_FOLDER, f"{invoice['invoice_number']}.pdf")

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    y = height - 40

    c.drawString(50, y, f"Invoice Number: {invoice['invoice_number']}")
    y -= 20
    c.drawString(50, y, f"Customer: {invoice['customer_name']}")
    y -= 20
    c.drawString(50, y, f"Date: {invoice['created_at']}")
    y -= 40

    c.drawString(50, y, "Items:")
    y -= 20

    for item in items:
        line = f"{item['name']} | Qty: {item['quantity']} | Price: {item['unit_price']} | Total: {item['line_total']}"
        c.drawString(50, y, line)
        y -= 20

    y -= 20
    c.drawString(50, y, f"Subtotal: {invoice['subtotal']}")
    y -= 20
    c.drawString(50, y, f"Tax: {invoice['tax']}")
    y -= 20
    c.drawString(50, y, f"Total: {invoice['total']}")

    c.save()

    cursor.execute(
        "UPDATE invoices SET pdf_path = ? WHERE id = ?",
        (file_path, invoice_id)
    )

    conn.commit()
    conn.close()

    return {"message": "PDF generated successfully"}

# ================= GET PDF =================
@app.get("/invoices")
def get_all_invoices():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/debug/invoices")
def debug_invoices():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/health")
def health_check():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        invoice, items = get_invoice_service(cursor, invoice_id)

    except ProductNotFoundError:
        raise HTTPException(status_code=404, detail="Invoice not found")

    finally:
        conn.close()

    return {
        "invoice": dict(invoice),
        "items": [dict(item) for item in items]
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}