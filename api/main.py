"""Housing CRM Backend API (Admin UI only for single table structure)"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

import pymssql
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse

DB_CONFIG = {
    "server": os.environ.get("DATABASE_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DATABASE_PORT", 1433)),
    "user": os.environ.get("DATABASE_USER", "housing"),
    "password": os.environ.get("DATABASE_PASSWORD", "housing123"),
    "database": os.environ.get("DATABASE_NAME", "housing"),
}
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="SAM Housing Service - Single Table UI")

def query(sql: str, params: tuple | None = None) -> list[dict]:
    # params=None skips %-substitution, so raw SQL with LIKE '%x%' works in the runner.
    conn = pymssql.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        results = []
        if cur.description:  # unnamed columns (e.g. COUNT(*)) get col1, col2...
            names = [d[0] or f"col{i + 1}" for i, d in enumerate(cur.description)]
            results = [dict(zip(names, row)) for row in cur.fetchall()]
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

@app.middleware("http")
async def log_agent_calls(request: Request, call_next):
    from starlette.concurrency import run_in_threadpool
    start = time.time()
    
    body = b""
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
        async def rcv(): return {"type": "http.request", "body": body}
        request._receive = rcv

    response = await call_next(request)
    ms = round((time.time() - start) * 1000, 1)

    if not request.url.path.startswith("/admin") and not request.url.path.startswith("/static") and request.url.path != "/":
        detail = unquote(request.url.query) if request.url.query else body.decode('utf-8', errors='ignore')
        if detail:
            detail = detail[:500]
        try:
            await run_in_threadpool(
                query, "INSERT INTO api_request_log (method, path, detail, status, duration_ms) VALUES (%s, %s, %s, %s, %s)",
                (request.method, unquote(request.url.path), detail or None, response.status_code, ms)
            )
        except Exception as e:
            print(f"Log err: {e}")
    return response

@app.get("/health", tags=["system"])
def health():
    query("SELECT 1")
    return {"status": "healthy", "service": "sam-housing-service"}

@app.post("/admin/query", include_in_schema=False)
async def execute_query(request: Request):
    """Raw SQL execution endpoint for the UI to run queries."""
    data = await request.json()
    sql = data.get("sql", "").strip()
    if not sql:
        raise HTTPException(status_code=400, detail="Empty query")
    try:
        results = query(sql)
        return _serialize(results)
    except Exception as e:
         raise HTTPException(status_code=400, detail=str(e))

@app.get("/admin/logs", include_in_schema=False)
def get_logs(limit: int = Query(200)):
    return _serialize(query("SELECT TOP (%s) * FROM api_request_log ORDER BY id DESC", (limit,)))

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
