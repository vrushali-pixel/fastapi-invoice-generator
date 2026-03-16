# Invoice Generator API

A production-grade invoice management REST API built with FastAPI, SQLite, and ReportLab.

## What this project demonstrates

- Layered architecture: routes → service → repository (separation of concerns)
- Atomic transactions: invoice creation rolls back fully if any item fails
- Custom domain exceptions: `ProductNotFoundError`, `InsufficientStockError`
- API key authentication via FastAPI dependency injection
- Multi-template PDF generation (standard / minimal / detailed)
- Aggregate stats endpoint with database-level computation
- Health check endpoint for deployment platforms

## Tech stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database | SQLite (PostgreSQL in v2) |
| PDF generation | ReportLab |
| Auth | API key via request header |
| Runtime | Python 3.10+ |

## Architecture

```
main.py        ← API layer: routes, request/response, HTTP status codes
service.py     ← Business logic: validation, calculations, orchestration
repository.py  ← Database layer: all SQL queries live here
schemas.py     ← Pydantic models: input validation and serialisation
security.py    ← Auth: API key verification via FastAPI Depends()
database.py    ← Connection factory
init_db.py     ← Schema creation on startup
```

## Key design decisions

**Atomic invoice creation** — the entire invoice (header + all items + stock deduction)
is wrapped in a single transaction. If stock is insufficient for item 3 of 5,
everything rolls back. The database never holds a partial invoice.

**Custom exceptions over generic ones** — raising `InsufficientStockError` in the
service layer and catching it in the route layer keeps business logic out of HTTP
handling. The service doesn't know or care about HTTP status codes.

**Database-level aggregation** — `/invoices/stats/summary` uses `COUNT()` and `SUM()`
in SQL rather than fetching all rows and computing in Python. Correct at any scale.

## Setup

```bash
git clone https://github.com/yourusername/invoice-generator-api
cd invoice-generator-api

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt

copy .env.example .env       # Windows
# cp .env.example .env       # Mac/Linux
# Edit .env and set your API_KEY

uvicorn main:app --reload
```

## API reference

All endpoints (except `/` and `/health`) require the header:
```
X-Api-Key: your-secret-key-here
```

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check (public) |
| POST | `/products` | Create a product |
| GET | `/products` | List all products |
| POST | `/invoices` | Create invoice (atomic) |
| GET | `/invoices` | List all invoices |
| GET | `/invoices/{id}` | Get invoice + items |
| GET | `/invoices/stats/summary` | Revenue and count stats |
| POST | `/invoices/{id}/pdf` | Generate PDF (`?template=standard\|minimal\|detailed`) |
| GET | `/invoices/{id}/pdf/download` | Download generated PDF |

Interactive docs: `http://localhost:8000/docs`

## Example: create an invoice

```bash
curl -X POST http://localhost:8000/invoices \
  -H "X-Api-Key: your-secret-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Rahul Sharma",
    "items": [
      {"product_id": 1, "quantity": 2},
      {"product_id": 3, "quantity": 1}
    ]
  }'
```

## Roadmap

- [ ] PostgreSQL migration
- [ ] JWT authentication (login / refresh tokens)
- [ ] Async PDF generation via Celery + Redis
- [ ] Email delivery of invoices
- [ ] Docker + docker-compose
- [ ] pytest test suite
- [ ] AI-powered invoice parsing (LLM extracts line items from text)
