# SAM Housing Service

Mock housing CRM for the **SAM (Solace Agent Mesh)** PoC. One **Microsoft SQL Server** table, `housing_data`,
loaded from `CRM Data_Solace_Anuj Version_DummyV2.xlsx` (133 bookings, HERO HOME TOWER 8).
SAM connects to SQL Server directly.

## Quick start

```bash
docker compose up -d --build --wait
```

| Open this | For |
|---|---|
| http://127.0.0.1:8000 | Data viewer UI + call log + SQL runner (T-SQL, runs as `housing`) |
| `127.0.0.1,1433` | SQL Server 2022 (Developer), database `housing` |

| Login | Password | Use |
|---|---|---|
| `sam_agent` | `sam_agent123` | SAM connector (least privilege) |
| `housing` | `housing123` | owner, used by the API/dashboard |
| `sa` | `Housing#Sa2026` | admin, used only by the seed container |

Use `127.0.0.1`, not `localhost`, on Windows (IPv6 fallback stalls ~20 s). The server uses a self-signed
certificate, so clients need **Trust Server Certificate** enabled.

```bash
python tests/smoke_test.py
```
```bash
python tests/data_check.py
```
`data_check.py` compares every cell with the Excel, checks formats, `sam_agent` permissions, the procedure and
the dashboard (resets `service_requests` when done).

Excel changed? Regenerate the seed and reset the DB (the seed only loads into an empty volume):

```bash
python generate_sql.py
```
```bash
docker compose down -v && docker compose up -d --build --wait
```

## Database

| Object | For | `sam_agent` access |
|---|---|---|
| `housing_data` | One row per booking. Dates are `DATE`, amounts `DECIMAL`, phones/IDs text | SELECT, **DENY** on Aadhaar/PAN columns |
| `service_requests` | Requests logged by the agent (`SR-00001`…) | SELECT |
| `raise_service_request @booking_no, @caller_phone, @category, @subject, @details` | Only write path; validates booking + category | EXECUTE |
| `api_request_log` | UI call log | none |
| `agent_queries` (Extended Events session) | Every statement and error from `sam_agent` | — |

The query to read `agent_queries` is in [tests/TEST_CASES.md](tests/TEST_CASES.md) ("Agent query log").

## Connect SAM

Full step-by-step with every connector setting: [sam/SETUP.md](sam/SETUP.md).

1. **Builder → Connectors → Create Connector → Microsoft SQL Server**: name `Housing CRM Database`,
   host `127.0.0.1`, port `1433`, database `housing`, user `sam_agent` / `sam_agent123`,
   trust server certificate on.
2. **Skills**: upload `Housing-MSSQL-Skill.zip` (built from `sam/skills/housing-mssql/`).
3. **Agent**: name `HousingAssistantAgent`, attach the connector + skill, paste
   [sam/agent-instructions.md](sam/agent-instructions.md) as the instructions.

Rebuild the zip after editing the skill:

```bash
sam skill validate housing-mssql sam/skills
```
```bash
sam skill package housing-mssql sam/skills -o Housing-MSSQL-Skill.zip
```

## Testing

See [tests/TEST_CASES.md](tests/TEST_CASES.md): the `Cases.pdf` scenarios, guardrail tests and the
dashboard queries that verify each answer. The agent verifies users by unit (or Booking No) + registered
mobile before sharing anything.

## Not in the data

Postal address, TDS records, payment transaction lines, sale deed, handover and registry dates. The agent
reports what exists and logs a service request for the rest.
