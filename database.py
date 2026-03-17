import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/invoice_db")

# ─────────────────────────────────────────────
# CONCEPT: RealDictCursor
# By default psycopg2 returns rows as tuples:
#   (1, "Laptop", 75000)
# RealDictCursor returns rows as dicts:
#   {"id": 1, "name": "Laptop", "price": 75000}
# This means row["name"] works instead of row[1]
# Same behaviour as SQLite's row_factory we had before.
# ─────────────────────────────────────────────

def get_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn