"""Mock housing CRM backend API for the SAM Housing PoC.

Agent endpoints for customer lookup, bookings, payments, documents, TDS and cases,
plus admin routes for the data viewer UI: browse/add/delete rows and a call log.
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

import mysql.connector
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

DB_CONFIG = {
    "host": os.environ.get("DATABASE_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DATABASE_PORT", 3306)),
    "user": os.environ.get("DATABASE_USER", "housing"),
    "password": os.environ.get("DATABASE_PASSWORD", "housing123"),
    "database": os.environ.get("DATABASE_NAME", "housing"),
}
MYSQL_LOG_FILE = os.environ.get("MYSQL_LOG_FILE")
STATIC = Path(__file__).parent / "static"
AGENT_PATHS = ("/customers/", "/bookings/", "/cases")

app = FastAPI(
    title="SAM Housing Service",
    version="1.0.0",
    description="Mock housing CRM API for the SAM PoC. "
    "Covers customer bookings, payments, documents, TDS records and case management. "
    "Customers are identified by phone number (E.164, e.g. +919876543201).",
)


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


def query_proc(proc_name: str, params: tuple = ()) -> list[dict]:
    """Call a stored procedure and return its result set."""
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(dictionary=True)
        cur.callproc(proc_name, params)
        results = []
        for result in cur.stored_results():
            results.extend(result.fetchall())
        conn.commit()
        return results
    finally:
        conn.close()


def mask_sensitive(text: str) -> str:
    """Hide PAN and Aadhaar-like patterns in logged text."""
    text = re.sub(r'[A-Z]{5}\d{4}[A-Z]', '**********', text)  # PAN
    return re.sub(r'\b\d{12}\b', '************', text)          # Aadhaar


@app.middleware("http")
async def log_agent_calls(request: Request, call_next):
    if not any(request.url.path.startswith(p) for p in AGENT_PATHS):
        return await call_next(request)
    body = (await request.body()).decode(errors="replace")
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    detail = mask_sensitive(request.url.query or body) or None
    await run_in_threadpool(
        query,
        "INSERT INTO api_request_log (method, path, detail, status, duration_ms) VALUES (%s, %s, %s, %s, %s)",
        (request.method, unquote(request.url.path), detail, response.status_code, ms))
    return response


def customer_or_404(phone: str) -> dict:
    rows = query("SELECT customer_id, full_name, phone, email, city FROM customers WHERE phone = %s", (phone,))
    if not rows:
        raise HTTPException(404, "CUSTOMER_NOT_FOUND")
    return rows[0]


def _serialize(rows: list[dict]) -> list[dict]:
    """Convert datetime/Decimal objects to JSON-safe types."""
    import decimal
    out = []
    for row in rows:
        d = {}
        for k, v in row.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
            elif isinstance(v, decimal.Decimal):
                d[k] = float(v)
            elif hasattr(v, 'isoformat'):
                d[k] = v.isoformat()
            else:
                d[k] = v
        out.append(d)
    return out


# ── Agent endpoints ─────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
def health():
    query("SELECT 1")
    return {"status": "healthy", "service": "sam-housing-service"}


@app.get("/customers/by-phone/{phone}", tags=["customer"], operation_id="get_customer_by_phone",
         summary="Look up a customer by phone number")
def get_customer(phone: str):
    return customer_or_404(phone)


@app.get("/customers/by-phone/{phone}/bookings", tags=["bookings"], operation_id="get_bookings",
         summary="List a customer's property bookings with unit and project details")
def get_bookings(phone: str):
    customer_or_404(phone)
    rows = query(
        "SELECT booking_id, booking_ref, booking_date, agreement_value, payment_plan, booking_status, "
        "unit_no, unit_type, block, floor_no, area_sqft, unit_status, "
        "project_code, project_name, project_location, project_city "
        "FROM customer_bookings WHERE phone = %s ORDER BY booking_date DESC", (phone,))
    return _serialize(rows)


@app.get("/bookings/{booking_id}/payments", tags=["payments"], operation_id="get_payments",
         summary="Payment history for a booking, newest first")
def get_payments(booking_id: int, phone: str = Query(..., description="Caller phone for ownership check")):
    # Scope to caller's bookings only
    if not query("SELECT 1 FROM customer_bookings WHERE phone = %s AND booking_id = %s", (phone, booking_id)):
        raise HTTPException(404, "BOOKING_NOT_FOUND")
    rows = query(
        "SELECT payment_id, amount, payment_date, payment_mode, receipt_no, tds_deducted, remarks "
        "FROM booking_payments WHERE booking_ref = "
        "(SELECT booking_ref FROM customer_bookings WHERE booking_id = %s LIMIT 1) "
        "ORDER BY payment_date DESC", (booking_id,))
    return _serialize(rows)


@app.get("/bookings/{booking_id}/payment-summary", tags=["payments"], operation_id="get_payment_summary",
         summary="Total paid, TDS and balance due for a booking")
def get_payment_summary(booking_id: int, phone: str = Query(..., description="Caller phone for ownership check")):
    # Look up booking_ref
    refs = query("SELECT booking_ref FROM customer_bookings WHERE phone = %s AND booking_id = %s",
                 (phone, booking_id))
    if not refs:
        raise HTTPException(404, "BOOKING_NOT_FOUND")
    result = query_proc("get_payment_summary", (phone, refs[0]["booking_ref"]))
    if result and not result[0].get("success", True):
        raise HTTPException(404, result[0].get("message", "BOOKING_NOT_FOUND"))
    return _serialize(result)[0] if result else {"error": "No data"}


@app.get("/bookings/{booking_id}/documents", tags=["documents"], operation_id="get_documents",
         summary="Document status for a booking (AFS, Sale Deed, Form 132, etc.)")
def get_documents(booking_id: int, phone: str = Query(..., description="Caller phone for ownership check")):
    if not query("SELECT 1 FROM customer_bookings WHERE phone = %s AND booking_id = %s", (phone, booking_id)):
        raise HTTPException(404, "BOOKING_NOT_FOUND")
    rows = query(
        "SELECT document_id, doc_type, doc_ref, doc_status, issued_at, dispatched_at, remarks "
        "FROM booking_documents WHERE booking_ref = "
        "(SELECT booking_ref FROM customer_bookings WHERE booking_id = %s LIMIT 1) "
        "ORDER BY doc_type", (booking_id,))
    return _serialize(rows)


@app.get("/bookings/{booking_id}/tds", tags=["tds"], operation_id="get_tds_records",
         summary="TDS submission records for a booking")
def get_tds_records(booking_id: int, phone: str = Query(..., description="Caller phone for ownership check")):
    if not query("SELECT 1 FROM customer_bookings WHERE phone = %s AND booking_id = %s", (phone, booking_id)):
        raise HTTPException(404, "BOOKING_NOT_FOUND")
    rows = query(
        "SELECT tds_id, financial_year, tds_amount, certificate_no, tds_status, submitted_at, remarks "
        "FROM booking_tds WHERE booking_ref = "
        "(SELECT booking_ref FROM customer_bookings WHERE booking_id = %s LIMIT 1) "
        "ORDER BY financial_year DESC", (booking_id,))
    return _serialize(rows)


@app.get("/customers/by-phone/{phone}/cases", tags=["cases"], operation_id="get_cases",
         summary="List all cases/complaints for a customer, newest first")
def get_cases(phone: str):
    customer_or_404(phone)
    rows = query(
        "SELECT case_id, case_ref, category, subject, case_status, priority, "
        "assigned_to, resolved_at, resolution, created_at, booking_ref, unit_no, project_name "
        "FROM customer_cases WHERE phone = %s ORDER BY created_at DESC", (phone,))
    return _serialize(rows)


class RaiseCaseRequest(BaseModel):
    phone: str = Field(description="Caller phone number, E.164", examples=["+919876543201"])
    booking_ref: str = Field("", description="Booking reference (optional, links case to a specific booking)")
    category: str = Field(description="Case category",
                          examples=["PAYMENT_UPDATE", "TDS_UPDATE", "DOCUMENT_REQUEST",
                                    "SALE_DEED_DELAY", "HANDOVER_INQUIRY", "REGISTRY_SCHEDULE", "GENERAL"])
    subject: str = Field(description="Brief subject line for the case", max_length=300)
    description: str = Field("", description="Detailed description of the issue")


@app.post("/cases", tags=["cases"], operation_id="raise_case",
          summary="Raise a new case/complaint for a customer")
def raise_case(req: RaiseCaseRequest):
    result = query_proc("raise_case", (req.phone, req.booking_ref or None, req.category,
                                        req.subject, req.description or None))
    if not result:
        raise HTTPException(500, "Failed to create case")
    row = result[0]
    if not row.get("success"):
        status = {"CUSTOMER_NOT_FOUND": 404, "BOOKING_NOT_FOUND": 404}.get(row.get("message", ""), 400)
        raise HTTPException(status, row.get("message", "UNKNOWN_ERROR"))
    return row


# ── Admin UI (not for agents; hidden from the OpenAPI spec) ─────────────────

ADMIN_TABLES = {
    "projects": "SELECT * FROM projects ORDER BY id",
    "units": "SELECT u.*, p.name AS project_name FROM units u JOIN projects p ON p.id = u.project_id ORDER BY u.id",
    "customers": "SELECT id, customer_id, full_name, phone, email, pan, city, created_at FROM customers ORDER BY id",
    "bookings": "SELECT b.*, c.full_name, u.unit_no FROM bookings b "
                "JOIN customers c ON c.id = b.customer_id JOIN units u ON u.id = b.unit_id ORDER BY b.id",
    "payments": "SELECT pay.*, b.booking_ref FROM payments pay "
                "JOIN bookings b ON b.id = pay.booking_id ORDER BY pay.payment_date DESC",
    "documents": "SELECT d.*, b.booking_ref FROM documents d "
                 "JOIN bookings b ON b.id = d.booking_id ORDER BY d.id",
    "tds_records": "SELECT t.*, b.booking_ref FROM tds_records t "
                   "JOIN bookings b ON b.id = t.booking_id ORDER BY t.id",
    "cases": "SELECT cs.*, c.full_name FROM cases cs "
             "JOIN customers c ON c.id = cs.customer_id ORDER BY cs.created_at DESC",
    "case_comments": "SELECT cc.*, cs.case_ref FROM case_comments cc "
                     "JOIN cases cs ON cs.id = cc.case_id ORDER BY cc.created_at DESC",
}

ADMIN_FORMS = {
    "projects": {"code": "text", "name": "text", "developer": "text", "location": "text",
                 "city": "text", "state": "text", "rera_no": "text"},
    "units": {"project_id": "number", "unit_no": "text",
              "unit_type": ["FLAT", "PLOT", "VILLA", "SHOP"],
              "block": "text", "floor_no": "number", "area_sqft": "number", "base_price": "number",
              "status": ["AVAILABLE", "BOOKED", "SOLD", "HANDEDOVER"]},
    "customers": {"customer_id": "text", "full_name": "text", "phone": "text", "email": "text",
                  "pan": "text", "city": "text"},
    "bookings": {"booking_ref": "text", "customer_id": "number", "unit_id": "number",
                 "booking_date": "date", "agreement_value": "number",
                 "payment_plan": ["CLP", "TLP", "FLEXI", "POSSESSION"],
                 "status": ["ACTIVE", "CANCELLED", "COMPLETED"]},
    "payments": {"booking_id": "number", "amount": "number", "payment_date": "date",
                 "payment_mode": ["CHEQUE", "NEFT", "RTGS", "UPI", "CASH", "DD"],
                 "receipt_no": "text", "tds_deducted": "number", "remarks": "text"},
    "documents": {"booking_id": "number",
                  "doc_type": ["AFS", "SALE_DEED", "FORM_132", "POSSESSION_LETTER", "NOC", "ALLOTMENT_LETTER"],
                  "doc_ref": "text",
                  "status": ["PENDING", "ISSUED", "SUBMITTED", "DISPATCHED", "RECEIVED"],
                  "remarks": "text"},
    "tds_records": {"booking_id": "number", "financial_year": "text", "amount": "number",
                    "certificate_no": "text",
                    "status": ["PENDING", "SUBMITTED", "VERIFIED", "REJECTED"],
                    "remarks": "text"},
    "cases": {"customer_id": "number", "booking_id": "number",
              "category": ["PAYMENT_UPDATE", "TDS_UPDATE", "DOCUMENT_REQUEST",
                           "SALE_DEED_DELAY", "HANDOVER_INQUIRY", "REGISTRY_SCHEDULE", "GENERAL"],
              "subject": "text", "description": "text",
              "status": ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", "ESCALATED"],
              "priority": ["LOW", "MEDIUM", "HIGH", "URGENT"],
              "assigned_to": "text"},
}

ADMIN_INSERTS = {
    "projects": "INSERT INTO projects (code, name, developer, location, city, state, rera_no) "
                "VALUES (%(code)s, %(name)s, %(developer)s, %(location)s, %(city)s, %(state)s, %(rera_no)s)",
    "units": "INSERT INTO units (project_id, unit_no, unit_type, block, floor_no, area_sqft, base_price, status) "
             "VALUES (%(project_id)s, %(unit_no)s, %(unit_type)s, %(block)s, %(floor_no)s, %(area_sqft)s, %(base_price)s, %(status)s)",
    "customers": "INSERT INTO customers (customer_id, full_name, phone, email, pan, city) "
                 "VALUES (%(customer_id)s, %(full_name)s, %(phone)s, %(email)s, %(pan)s, %(city)s)",
    "bookings": "INSERT INTO bookings (booking_ref, customer_id, unit_id, booking_date, agreement_value, payment_plan, status) "
                "VALUES (%(booking_ref)s, %(customer_id)s, %(unit_id)s, %(booking_date)s, %(agreement_value)s, %(payment_plan)s, %(status)s)",
    "payments": "INSERT INTO payments (booking_id, amount, payment_date, payment_mode, receipt_no, tds_deducted, remarks) "
                "VALUES (%(booking_id)s, %(amount)s, %(payment_date)s, %(payment_mode)s, %(receipt_no)s, %(tds_deducted)s, %(remarks)s)",
    "documents": "INSERT INTO documents (booking_id, doc_type, doc_ref, status, remarks) "
                 "VALUES (%(booking_id)s, %(doc_type)s, %(doc_ref)s, %(status)s, %(remarks)s)",
    "tds_records": "INSERT INTO tds_records (booking_id, financial_year, amount, certificate_no, status, remarks) "
                   "VALUES (%(booking_id)s, %(financial_year)s, %(amount)s, %(certificate_no)s, %(status)s, %(remarks)s)",
    "cases": "INSERT INTO cases (case_ref, customer_id, booking_id, category, subject, description, status, priority, assigned_to) "
             "VALUES (CONCAT('CASE-', DATE_FORMAT(NOW(), '%%Y%%m%%d'), '-', UPPER(SUBSTRING(MD5(RAND()), 1, 6))), "
             "%(customer_id)s, %(booking_id)s, %(category)s, %(subject)s, %(description)s, %(status)s, %(priority)s, %(assigned_to)s)",
}

ADMIN_DELETES = {
    "projects": "DELETE FROM projects WHERE id = %s",
    "units": "DELETE FROM units WHERE id = %s",
    "customers": "DELETE FROM customers WHERE id = %s",
    "bookings": "DELETE FROM bookings WHERE id = %s",
    "payments": "DELETE FROM payments WHERE id = %s",
    "documents": "DELETE FROM documents WHERE id = %s",
    "tds_records": "DELETE FROM tds_records WHERE id = %s",
    "cases": "DELETE FROM cases WHERE id = %s",
    "case_comments": "DELETE FROM case_comments WHERE id = %s",
}


def admin_write(sql: str, params) -> int:
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        last_id = cur.lastrowid
        conn.commit()
        return last_id
    except mysql.connector.Error as e:
        raise HTTPException(400, str(e.msg))
    finally:
        conn.close()


@app.get("/admin/tables/{name}", include_in_schema=False)
def admin_table(name: str):
    if name not in ADMIN_TABLES:
        raise HTTPException(404, "UNKNOWN_TABLE")
    return _serialize(query(ADMIN_TABLES[name]))


@app.get("/admin/forms", include_in_schema=False)
def admin_forms():
    return {"forms": ADMIN_FORMS, "deletable": list(ADMIN_DELETES)}


@app.post("/admin/tables/{name}", include_in_schema=False)
def admin_add(name: str, body: dict[str, str | int | float | None]):
    if name not in ADMIN_INSERTS:
        raise HTTPException(404, "UNKNOWN_TABLE")
    params = {f: (body.get(f) if body.get(f) != "" else None) for f in ADMIN_FORMS.get(name, {})}
    last_id = admin_write(ADMIN_INSERTS[name], params)
    if not last_id:
        raise HTTPException(400, "Insert failed")
    return {"id": last_id}


@app.delete("/admin/tables/{name}/{row_id}", include_in_schema=False)
def admin_delete(name: str, row_id: int):
    if name not in ADMIN_DELETES:
        raise HTTPException(404, "UNKNOWN_TABLE")
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(ADMIN_DELETES[name], (row_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "ROW_NOT_FOUND")
        conn.commit()
        return {"deleted": row_id}
    except mysql.connector.Error as e:
        raise HTTPException(400, str(e.msg))
    finally:
        conn.close()


# ── Call log ────────────────────────────────────────────────────────────────

@app.get("/admin/logs", include_in_schema=False)
def admin_logs(limit: int = Query(200, ge=1, le=2000)):
    api_rows = [{
        "logged_at": r["created_at"].isoformat() if isinstance(r["created_at"], datetime) else str(r["created_at"]),
        "source": "API",
        "request": f"{r['method']} {r['path']}" + (f"  {r['detail']}" if r.get("detail") else ""),
        "result": str(r["status"]),
        "ms": float(r["duration_ms"]),
    } for r in query("SELECT * FROM api_request_log ORDER BY id DESC LIMIT %s", (limit,))]
    return sorted(api_rows, key=lambda r: r["logged_at"], reverse=True)[:limit]


@app.get("/", include_in_schema=False)
def ui():
    return FileResponse(STATIC / "index.html")
