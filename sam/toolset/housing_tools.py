#!/usr/bin/env python3
"""
housing_tools.py — SAM toolset that exposes the SAM Housing Service REST API as agent tools.

SAM STR protocol (same as bank_tools.py):
  --schema              → print JSON schema for all tools, then exit
  <runner_args.json>    → read args, execute tool, write result to result_file path

Base URL defaults to http://127.0.0.1:8000; override with the HOUSING_API_URL env var.
(127.0.0.1, not localhost: on Windows localhost tries IPv6 first and Docker Desktop stalls ~20s on it.)
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = os.environ.get("HOUSING_API_URL", "http://127.0.0.1:8000").rstrip("/")

PHONE = {"type": "string", "description": "Customer phone number in E.164 format, e.g. +919876543201"}


def tool(description, properties, required):
    return {"description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
            "artifact_params": {}, "instructions": ""}


SCHEMA = {"tools": {
    "get_customer": tool("Look up the customer (ID, name, city, email) for a caller phone number.",
                         {"phone": PHONE}, ["phone"]),
    "get_bookings": tool("List the customer's property bookings with unit and project details.",
                         {"phone": PHONE}, ["phone"]),
    "get_payments": tool(
        "Payment history for a specific booking, newest first. Shows amount, date, mode, TDS deducted.",
        {"phone": PHONE,
         "booking_id": {"type": "integer", "description": "Booking ID (from get_bookings results)"}},
        ["phone", "booking_id"]),
    "get_payment_summary": tool(
        "Total paid, total TDS deducted, and balance due for a booking.",
        {"phone": PHONE,
         "booking_id": {"type": "integer", "description": "Booking ID (from get_bookings results)"}},
        ["phone", "booking_id"]),
    "get_documents": tool(
        "Document status for a booking (AFS, Sale Deed, Form 132, Possession Letter, etc.).",
        {"phone": PHONE,
         "booking_id": {"type": "integer", "description": "Booking ID (from get_bookings results)"}},
        ["phone", "booking_id"]),
    "get_tds_records": tool(
        "TDS submission records for a booking, by financial year.",
        {"phone": PHONE,
         "booking_id": {"type": "integer", "description": "Booking ID (from get_bookings results)"}},
        ["phone", "booking_id"]),
    "get_cases": tool("List all cases/complaints raised by the customer, newest first.",
                      {"phone": PHONE}, ["phone"]),
    "raise_case": tool(
        "Raise a new case/complaint for the customer. Returns a case reference number.",
        {"phone": PHONE,
         "booking_ref": {"type": "string", "description": "Booking reference to link the case to (optional)"},
         "category": {"type": "string",
                      "description": "PAYMENT_UPDATE, TDS_UPDATE, DOCUMENT_REQUEST, SALE_DEED_DELAY, "
                                     "HANDOVER_INQUIRY, REGISTRY_SCHEDULE, or GENERAL"},
         "subject": {"type": "string", "description": "Brief subject line (max 300 chars)"},
         "description": {"type": "string", "description": "Detailed description of the issue (optional)"}},
        ["phone", "category", "subject"]),
}}


def http(method, path, body=None):
    req = urllib.request.Request(BASE_URL + path, method=method,
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return {"result": {"status": "success", "data": json.load(r)}, "error": ""}
    except urllib.error.HTTPError as e:
        return {"result": None, "error": f"HTTP {e.code}: {json.load(e).get('detail')}"}
    except urllib.error.URLError as e:
        return {"result": None, "error": f"Housing backend unreachable at {BASE_URL}: {e.reason}"}


def q(value):
    return urllib.parse.quote(str(value), safe="")


TOOLS = {
    "get_customer": lambda a: http("GET", f"/customers/by-phone/{q(a['phone'])}"),
    "get_bookings": lambda a: http("GET", f"/customers/by-phone/{q(a['phone'])}/bookings"),
    "get_payments": lambda a: http("GET", f"/bookings/{int(a['booking_id'])}/payments?phone={q(a['phone'])}"),
    "get_payment_summary": lambda a: http("GET", f"/bookings/{int(a['booking_id'])}/payment-summary?phone={q(a['phone'])}"),
    "get_documents": lambda a: http("GET", f"/bookings/{int(a['booking_id'])}/documents?phone={q(a['phone'])}"),
    "get_tds_records": lambda a: http("GET", f"/bookings/{int(a['booking_id'])}/tds?phone={q(a['phone'])}"),
    "get_cases": lambda a: http("GET", f"/customers/by-phone/{q(a['phone'])}/cases"),
    "raise_case": lambda a: http("POST", "/cases", {
        k: a[k] for k in ("phone", "booking_ref", "category", "subject", "description") if a.get(k)}),
}


def main():
    args = sys.argv[1:]
    if args and args[0] == "--schema":
        print(json.dumps(SCHEMA))
        return
    if not args:
        sys.exit("usage: housing_tools.py --schema | <runner_args.json>")

    with open(args[0]) as f:
        runner_args = json.load(f)
    name = runner_args.get("tool_name", "")
    handler = TOOLS.get(name)
    try:
        result = handler(runner_args.get("args", {})) if handler else {"result": None, "error": f"tool '{name}' not found"}
    except Exception as e:
        result = {"result": None, "error": f"tool '{name}' raised an exception: {e}"}

    if runner_args.get("result_file"):
        with open(runner_args["result_file"], "w") as f:
            json.dump(result, f, default=str)
    else:
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
