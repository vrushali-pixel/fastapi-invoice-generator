from fastapi import Header, HTTPException, Depends
import os

API_KEY = os.getenv("API_KEY", "supersecretkey")

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")