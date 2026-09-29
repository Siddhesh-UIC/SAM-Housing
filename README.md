# SAM Housing Service

Mock housing CRM for the **SAM (Solace Agent Mesh)** PoC. One MySQL table, `housing_data`, loaded from
`CRM Data_Solace_Anuj Version_DummyV2.xlsx` (133 bookings, HERO HOME TOWER 8). SAM connects to MySQL directly.

## Quick start

```bash
docker compose up -d --build --wait
```

| Open this | For |
|---|---|
| http://127.0.0.1:8000 | Data viewer UI + call log + SQL runner |
| `127.0.0.1:3306` | MySQL `housing` — owner `housing`/`housing123`, agent `sam_agent`/`sam_agent123` |

Use `127.0.0.1`, not `localhost`, on Windows (IPv6 fallback stalls ~20 s).

```bash
python tests/smoke_test.py
```

Excel changed? Regenerate the seed and reset the DB:

```bash
python generate_sql.py
```
```bash
docker compose down -v && docker compose up -d --build --wait
```

## Database

| Object | For | `sam_agent` access |
|---|---|---|
| `housing_data` | One row per booking. Dates are `DATE`, amounts `DECIMAL`, phones/IDs text | SELECT on all columns **except** Aadhaar/PAN |
| `service_requests` | Requests logged by the agent (`SR-00001`…) | SELECT |
| `raise_service_request(booking_no, phone, category, subject, details)` | Only write path; validates booking + category | EXECUTE |
| `api_request_log` | UI call log | none |

## Connect SAM

1. **Builder → Connectors → Create Connector → MySQL**: name `Housing CRM Database`, host `127.0.0.1`,
   port `3306`, database `housing`, user `sam_agent` / `sam_agent123`.
2. **Skills**: upload `Housing-MySql-Skill.zip` (built from `sam/skills/housing-mysql/`).
3. **Agent**: name `HousingAssistantAgent`, attach the connector + skill, paste
   [sam/agent-instructions.md](sam/agent-instructions.md) as the instructions.

Rebuild the zip after editing the skill:

```bash
sam skill validate housing-mysql sam/skills
```
```bash
sam skill package housing-mysql sam/skills -o Housing-MySql-Skill.zip
```

### Test prompts

The agent verifies users by unit (or Booking No) + registered mobile before sharing anything.
Pick a test customer from the data viewer UI (`UnitCode` + `MobileNo1`) and start each test in a new chat:

```
Kindly update balance payment of my flat. TDS not required, it is under 50 lakh.
```
```
Please confirm the earliest handover date of my flat and what is required from me.
```
```
Please send my AFS to my communication address, I can't collect it from the office.
```
```
Please schedule my registry on Monday 14/9/2026.
```
Each should make the agent ask for unit + mobile first. Check its figures against the same row in the UI.

## Not in the data

TDS records, payment transaction lines, sale deed, handover and registry dates. The agent reports what
exists and logs a service request for the rest.
