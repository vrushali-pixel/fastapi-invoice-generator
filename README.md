# FastAPI Invoice Generator

A backend system for managing products and generating invoices with PDF export.

## Features

- Product management
- Invoice creation
- Automatic stock deduction
- PDF invoice generation
- API key authentication
- SQLite database
- FastAPI automatic documentation
- RESTful API design

## Tech Stack

- Python
- FastAPI
- SQLite
- ReportLab
- Postman

## Installation

```bash
git clone https://github.com/yourusername/fastapi-invoice-generator.git
cd fastapi-invoice-generator

pip install -r requirements.txt
uvicorn main:app --reload
```

## API Documentation

FastAPI automatically generates docs.

Open:

```
http://127.0.0.1:8000/docs
```

## Endpoints

| Method | Endpoint | Description |
|------|------|------|
| POST | /products | Create product |
| GET | /products | List products |
| POST | /invoices | Create invoice |
| GET | /invoices | List invoices |
| POST | /invoices/{id}/pdf | Generate invoice PDF |

## Example Invoice Request

```json
{
  "customer_name": "Test Customer",
  "items": [
    {
      "product_id": 2,
      "quantity": 1
    }
  ]
}
```

## Project Structure

```
routes → API layer
service → business logic
repository → database queries

```


## API Testing

A Postman collection is included in the repository.

Import the file:

invoice_api_collection.json

Then run the API locally:

uvicorn main:app --reload

Base URL:
http://127.0.0.1:8000

http://127.0.0.1:8000/docs
