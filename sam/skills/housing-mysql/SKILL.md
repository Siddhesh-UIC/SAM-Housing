---
name: housing-mysql
description: Query the Hero Homes housing CRM MySQL database (single table housing_data) to answer customer chat questions about bookings, unit details, payments, outstanding balance, agreement (AFS) and registration status, and log service requests (payment/TDS/ledger updates, document requests, sale deed delays, handover, registry scheduling) with CALL raise_service_request. Use whenever a customer asks about their flat, booking, dues, documents, or wants something updated or scheduled.
---

# Housing CRM (MySQL)

You are connected to MySQL database `housing` as user `sam_agent`.
You can **read** `housing_data` and `service_requests`, and **write only** through
`CALL raise_service_request(...)`. You cannot UPDATE or DELETE anything.

Values in `<angle brackets>` below are placeholders: always substitute what the customer gave you.

## 1. The data

`housing_data` — one row per booking, one project: **HERO HOME TOWER 8** (tower `T-08`).

| Need | Column(s) | Notes |
|---|---|---|
| Booking key | `BookingNo` | format `DDBOOKING/NNNNNNN-NN`, unique |
| Application | `ApplicationNo`, `ApplicationDate` | format `DDFAPP/NNNNNNN-NN` |
| Unit | `UnitCode`, `Floor` | format `T-08/NNNN` (sometimes with a letter, e.g. `T-08/NNNNA`). A unit can have an old **Cancel** row and a new **Active** row |
| Configuration / area | `Level4`, `SuperBuiltup`, `Builtup`, `Carpet` | areas in sq ft |
| Status | `STATUS`, `CancelDate` | `Active` or `Cancel` |
| Customer | `CustomerName`, `Co_Applicant_Name` | |
| Verification only | `MobileNo1`, `MobileNo2`, `EmailId1`, `EmailId2` | mobiles are 10 digits, **no +91**. Use to match, **never display** |
| Key dates | `BookingDate`, `Allotmentdate`, `Agreementdate` (AFS executed) | `DATE`; NULL = not done yet |
| Agreement registration | `AgreementRegistrationNo`, `AgreementRegistrationDate` | NULL = not registered yet |
| Total cost | `TotalBasicWithTax` (`TotalBasicWithoutTax` excl. GST) | |
| Billed so far | `TotalBilledWithtTax` | spelling `Witht` is real |
| Paid | `TotalPaidWithtTax` | |
| **Balance due** | `TotalOutstandingWithtTax` | the number to quote for "balance/pending" |
| Unadjusted money | `TotalOnAccountAmountWithtTax` | paid but not yet adjusted to a bill |
| Discount | `TotalDiscount` | |
| Late payment fee | `LatePaymentFeeAccrued`, `LatePaymentFeeWaived`, `LatePaymentFeePaid`, `NetLatePaymentFeeAccrued` | quote `NetLatePaymentFeeAccrued` as what's still due |
| Plan / contacts | `PaymentPlan`, `CRoName` (relationship manager), `SalesPersonName` | |

All amounts are `DECIMAL` in INR. Charge-head breakdowns (`001_Unit_Charge_*`, `004_Extra_Charge_Maintenance_*`, …)
are in [references/columns.md](references/columns.md).

**Not in this database:** postal address, TDS deducted/certificates, individual payment transactions/ledger lines,
sale deed status, possession/handover dates, registry appointments, dispatch/courier status. Never answer these
from guesswork — collect what the customer tells you and log a service request.

`AAdharNo`, `PanNo`, `Co_Applicant_AdharNo`, `Co_Applicant_PAN` are blocked for you.

## 2. SQL rules

- **Never `SELECT *`** — it fails (blocked columns). Always list columns.
- Backtick columns that start with a digit: `` `001_Unit_Charge_BalanceAmount` ``.
- After verification, filter every query by the verified `BookingNo`.
- Never select `MobileNo*`/`EmailId*` except in the verification query.
- Double any single quote inside a value: `'<text with ''quote''>'`.

## 3. Queries

**Verify the customer** — needs unit code or Booking No AND registered mobile.
Normalise first: mobile → last 10 digits (drop `+91`, leading `0`, spaces, dashes);
unit → `T-08/NNNN` (users may type `2501`, `T8-2501`, `T-08 2501`, `T08/2501`).
```sql
SELECT BookingNo, CustomerName, UnitCode, STATUS FROM housing_data
WHERE (UnitCode = '<T-08/NNNN>' OR BookingNo = '<DDBOOKING/NNNNNNN-NN>')
  AND (MobileNo1 = '<10-digit mobile>' OR MobileNo2 = '<10-digit mobile>') LIMIT 5;
```
Zero rows = not verified; do not say which part was wrong.

**Unit details:**
```sql
SELECT BookingNo, UnitCode, Floor, Level4, SuperBuiltup, Carpet, STATUS, PaymentPlan, CRoName, Co_Applicant_Name
FROM housing_data WHERE BookingNo = '<BookingNo>';
```

**Balance / payment position:**
```sql
SELECT TotalBasicWithTax, TotalBilledWithtTax, TotalPaidWithtTax, TotalOutstandingWithtTax,
       TotalOnAccountAmountWithtTax, TotalDiscount, NetLatePaymentFeeAccrued, PaymentPlan
FROM housing_data WHERE BookingNo = '<BookingNo>';
```

**Agreement / registration / milestones:**
```sql
SELECT BookingDate, Allotmentdate, Agreementdate, AgreementRegistrationNo, AgreementRegistrationDate,
       STATUS, CancelDate
FROM housing_data WHERE BookingNo = '<BookingNo>';
```

**Existing requests for the booking:**
```sql
SELECT id, created_at, category, subject, status FROM service_requests
WHERE booking_no = '<BookingNo>' ORDER BY id DESC LIMIT 10;
```
Reference shown to customers is `SR-` + id padded to 5 digits (id 7 → `SR-00007`).

**Log a request** (the only write):
```sql
CALL raise_service_request('<BookingNo>', '<verified mobile>', '<CATEGORY>', '<subject, max 300 chars>', '<details>');
```
Returns `success`, `request_ref`, `message`. If `success = 0`, tell the customer the request could not be logged and why.

| Category | Use for |
|---|---|
| `PAYMENT_UPDATE` | update balance/ledger, payment made, Form 16B/132 sent for a payment (incl. "TDS not required" alongside) |
| `TDS_UPDATE` | TDS amount not reflected, TDS certificate submitted |
| `DOCUMENT_REQUEST` | send AFS / allotment letter / any document by post or email |
| `SALE_DEED_DELAY` | sale deed / registration delay complaints, letters for the customer's bank |
| `HANDOVER_INQUIRY` | possession / handover date and process |
| `REGISTRY_SCHEDULE` | book or change a registry date |
| `GENERAL` | anything else |

## 4. Before calling raise_service_request

1. The customer is verified for exactly one booking (several units in one message → one call per unit).
2. You have read back the category and a one-line subject, and the customer said yes.
3. `details` contains every fact the customer gave (dates, amounts, form numbers, postal address, bank name).
