"""Housing CRM Backend API (Admin UI only for single table structure)"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

import mysql.connector
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse

DB_CONFIG = {
    "host": os.environ.get("DATABASE_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DATABASE_PORT", 3306)),
    "user": os.environ.get("DATABASE_USER", "housing"),
    "password": os.environ.get("DATABASE_PASSWORD", "housing123"),
    "database": os.environ.get("DATABASE_NAME", "housing"),
}
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="SAM Housing Service - Single Table UI")

def query(sql: str, params: tuple = (), dictionary: bool = True) -> list[dict]:
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(dictionary=dictionary)
        cur.execute(sql, params)
        results = []
        try:
            results = cur.fetchall()
        except mysql.connector.errors.InterfaceError:
            pass
        conn.commit()
        return results
    finally:
        conn.close()

def _serialize(rows: list[dict]) -> list[dict]:
    import decimal
    out = []
    for row in rows:
        d = {}
        for k, v in row.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
            elif hasattr(v, 'isoformat'):
                d[k] = v.isoformat()
            else:
                d[k] = str(v) if v is not None else ""
        out.append(d)
    return out

@app.get("/health", tags=["system"])
def health():
    query("SELECT 1")
    return {"status": "healthy", "service": "sam-housing-service"}

@app.get("/admin/tables/housing_data", include_in_schema=False)
def get_housing_data():
    return _serialize(query("SELECT * FROM housing_data"))

@app.get("/admin/forms", include_in_schema=False)
def admin_forms():
    # We aren't fully supporting insert/delete via UI anymore for the massive flat table, just reading.
    return {"forms": {}, "deletable": []}

@app.get("/", include_in_schema=False)
def ui():
    return FileResponse(STATIC / "index.html")
