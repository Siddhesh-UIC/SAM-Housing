#!/usr/bin/env python3
"""Smoke test for the SAM Housing Service API.

Run with the containers up:  python tests/smoke_test.py
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"
PHONE = "+919876543201"    # Rajesh Kumar Sharma
PHONE2 = "+919876543204"   # Sunita Devi
PASS = 0
FAIL = 0


def q(v):
    return urllib.parse.quote(str(v), safe="")


def test(label, method, path, expected_status=200, body=None):
    global PASS, FAIL
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, method=method, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.load(r)
            status = r.status
    except urllib.error.HTTPError as e:
        result = json.load(e) if e.headers.get("content-type", "").startswith("application/json") else {"detail": e.read().decode()}
        status = e.code

    ok = status == expected_status
    icon = "✓" if ok else "✗"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f"  {icon} {label:50s}  HTTP {status}" + ("" if ok else f"  (expected {expected_status})"))
    if not ok:
        print(f"    Response: {json.dumps(result, indent=2, default=str)[:300]}")
    return result


def main():
    print("\n=== SAM Housing Service — Smoke Test ===\n")

    # Health
    test("Health check", "GET", "/health")

    # Customer lookup
    print("\n— Customer lookup —")
    test("Get customer by phone", "GET", f"/customers/by-phone/{q(PHONE)}")
    test("Unknown phone → 404", "GET", f"/customers/by-phone/{q('+910000000000')}", 404)

    # Bookings
    print("\n— Bookings —")
    bookings = test("Get bookings (Rajesh)", "GET", f"/customers/by-phone/{q(PHONE)}/bookings")
    booking_id = bookings[0]["booking_id"] if bookings else None
    print(f"    → Found {len(bookings)} booking(s), first id={booking_id}")

    # Payments
    print("\n— Payments —")
    if booking_id:
        payments = test("Get payments", "GET", f"/bookings/{booking_id}/payments?phone={q(PHONE)}")
        print(f"    → {len(payments)} payment(s)")
        test("Payment summary", "GET", f"/bookings/{booking_id}/payment-summary?phone={q(PHONE)}")
    test("Wrong phone → 404", "GET", f"/bookings/1/payments?phone={q('+910000000000')}", 404)

    # Documents
    print("\n— Documents —")
    if booking_id:
        docs = test("Get documents", "GET", f"/bookings/{booking_id}/documents?phone={q(PHONE)}")
        print(f"    → {len(docs)} document(s)")

    # TDS Records
    print("\n— TDS Records —")
    if booking_id:
        tds = test("Get TDS records", "GET", f"/bookings/{booking_id}/tds?phone={q(PHONE)}")
        print(f"    → {len(tds)} TDS record(s)")

    # Cases
    print("\n— Cases —")
    cases = test("Get cases (Rajesh)", "GET", f"/customers/by-phone/{q(PHONE)}/cases")
    print(f"    → {len(cases)} case(s)")

    cases2 = test("Get cases (Sunita)", "GET", f"/customers/by-phone/{q(PHONE2)}/cases")
    print(f"    → {len(cases2)} case(s)")

    # Raise a new case
    print("\n— Raise case —")
    new_case = test("Raise case", "POST", "/cases", body={
        "phone": PHONE,
        "booking_ref": "BK-2023-001",
        "category": "GENERAL",
        "subject": "Smoke test case",
        "description": "This is an automated smoke test case."
    })
    if new_case.get("case_ref"):
        print(f"    → Created: {new_case['case_ref']}")

    test("Raise case unknown phone → 404", "POST", "/cases", 404, body={
        "phone": "+910000000000",
        "category": "GENERAL",
        "subject": "Should fail"
    })

    test("Raise case unknown booking → 404", "POST", "/cases", 404, body={
        "phone": PHONE,
        "booking_ref": "BK-9999-999",
        "category": "GENERAL",
        "subject": "Should fail"
    })

    # Admin endpoints
    print("\n— Admin —")
    test("Admin tables (projects)", "GET", "/admin/tables/projects")
    test("Admin forms", "GET", "/admin/forms")
    test("Admin logs", "GET", "/admin/logs?limit=10")

    # Summary
    print(f"\n{'='*50}")
    total = PASS + FAIL
    print(f"  {PASS}/{total} passed, {FAIL} failed")
    if FAIL:
        print("  ⚠ Some tests failed!")
        sys.exit(1)
    else:
        print("  ✓ All tests passed!")


if __name__ == "__main__":
    main()
