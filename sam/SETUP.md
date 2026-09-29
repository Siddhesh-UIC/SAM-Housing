# SAM setup — HousingAssistantAgent

## 1. Start the database

```bash
docker compose up -d --build --wait
```
```bash
python tests/smoke_test.py
```

First start loads the seed (133 bookings). To reload from scratch: `docker compose down -v` then the command above.

## 2. Connector

**SAM → Builder → Connectors → Create Connector → Microsoft SQL Server**

| Field | Value |
|---|---|
| Connector Name | `Housing CRM Database` |
| Description | `Hero Homes Tower 8 housing CRM (SQL Server). Table housing_data (bookings, balances, agreement registration); service_requests; EXEC raise_service_request to log requests.` |
| Host | `127.0.0.1` |
| Port | `1433` |
| Database | `housing` |
| Username | `sam_agent` |
| Password | `sam_agent123` |
| Encrypt | on (if the connector asks) |
| Trust Server Certificate | **on** — the server uses a self-signed certificate; the connection fails without it |

Use `127.0.0.1`, not `localhost` (Windows IPv6 fallback stalls ~20 s). If SAM runs in Docker on the same
machine, use `host.docker.internal` as the host.

`sam_agent` can only: read `housing_data` (Aadhaar/PAN columns denied), read `service_requests`, and
`EXEC raise_service_request`. No UPDATE/INSERT/DELETE.

Other logins (don't give these to SAM):

| Login | Password | Used by |
|---|---|---|
| `housing` | `housing123` | dashboard / API (owner) |
| `sa` | `Housing#Sa2026` | seed container only |

## 3. Skill

1. Build the zip (skip if `Housing-MSSQL-Skill.zip` is current):
   ```bash
   sam skill package housing-mssql sam/skills -o Housing-MSSQL-Skill.zip
   ```
2. **SAM → Skills → Upload skill** → `Housing-MSSQL-Skill.zip`.
3. Remove any old `housing-mysql` skill.

## 4. Agent

**SAM → Builder → Agent Management → Add Agent → Create Manually**

| Field | Value |
|---|---|
| Name | `HousingAssistantAgent` |
| Description | `Hero Homes customer chat support: booking, balance, agreement status; logs service requests.` |
| Connector | `Housing CRM Database` |
| Skill | `housing-mssql` |
| Instructions | paste all of [agent-instructions.md](agent-instructions.md) |

## 5. Check it works

1. Start a **new chat**: `What is my pending balance?` → it should ask for unit + registered mobile.
2. Pick a test customer and verify answers with the queries in [../tests/TEST_CASES.md](../tests/TEST_CASES.md).
3. Dashboard http://127.0.0.1:8000 → SQL runner → run the **Agent query log** query from TEST_CASES.md
   to see the exact SQL the agent ran and any errors.

| Symptom | Cause / fix |
|---|---|
| Agent says "connectivity issue" | Check the Agent query log: usually wrong column names or `SELECT *`. Re-paste instructions, new chat. |
| Connector test fails with a certificate error | Turn on Trust Server Certificate. |
| Login failed for `sam_agent` | Database not seeded — `docker compose down -v` then `up`. |
| Agent asks for name instead of mobile | Old instructions or old chat — re-paste, start a new chat. |
