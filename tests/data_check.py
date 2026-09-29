"""Full check: every cell vs Excel, formats, sam_agent permissions, procedure, dashboard. Run from repo root, containers up."""
import json, os, re, subprocess, urllib.request as u
from decimal import Decimal
import pandas as pd

os.environ['MSYS_NO_PATHCONV'] = '1'
results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(('PASS ' if ok else 'FAIL ') + name + (f'  -> {detail}' if detail and not ok else ''))


def q(sql):
    r = u.Request('http://127.0.0.1:8000/admin/query', json.dumps({'sql': sql}).encode(), {'Content-Type': 'application/json'})
    return json.load(u.urlopen(r))


def agent(sql):
    r = subprocess.run(['docker', 'exec', 'sam-housing-db', '/opt/mssql-tools18/bin/sqlcmd', '-S', 'localhost', '-U', 'sam_agent',
                        '-P', 'sam_agent123', '-d', 'housing', '-C', '-b', '-h', '-1', '-W', '-s', '|', '-Q', 'SET NOCOUNT ON; ' + sql],
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


# ---------- 1. Data: every cell vs Excel ----------
df = pd.read_excel('CRM Data_Solace_Anuj Version_DummyV2.xlsx')
names = {c: c.replace('.', '_') for c in df.columns}
db = q('SELECT * FROM housing_data ORDER BY id')
types = {r['COLUMN_NAME']: r['DATA_TYPE'] for r in q("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='housing_data'")}
DATES = {'BookingDate', 'ApplicationDate', 'Agreementdate', 'Allotmentdate', 'CancelDate', 'AgreementRegistrationDate'}
IDS = {'AAdharNo', 'MobileNo1', 'MobileNo2', 'Co_Applicant_AdharNo', 'Bookingid', 'AgreementRegistrationNo'}

check('row count 133', len(db) == len(df) == 133, f'db={len(db)} excel={len(df)}')
check('column count 125 (+id)', len(types) == len(df.columns) + 1, len(types))

bad_types = []
for c in df.columns:
    want = 'date' if c in DATES else 'nvarchar' if c in IDS or not pd.api.types.is_numeric_dtype(df[c]) or df[c].isna().all() else 'decimal'
    if types.get(names[c]) != want:
        bad_types.append(f'{names[c]}={types.get(names[c])} want {want}')
check('column types (DATE / DECIMAL / NVARCHAR)', not bad_types, bad_types[:5])


def expect(c, v):
    if pd.isna(v) or (isinstance(v, str) and not v.strip()):
        return ''
    if c in DATES:
        d = pd.Timestamp('1899-12-30') + pd.Timedelta(days=v) if isinstance(v, (int, float)) else pd.Timestamp(v)
        return d.strftime('%Y-%m-%d')
    if c in IDS:
        return str(int(v)) if isinstance(v, float) else str(v)
    if types[names[c]] == 'decimal':
        return Decimal(str(v)).quantize(Decimal('0.01'))
    return str(v).strip()


diffs = []
for i, (_, row) in enumerate(df.iterrows()):
    for c in df.columns:
        got, want = db[i][names[c]], expect(c, row[c])
        if isinstance(want, Decimal) and got != '':
            got = Decimal(got).quantize(Decimal('0.01'))
        if got != want:
            diffs.append(f'row {i + 1} {names[c]}: {got!r} vs {want!r}')
check(f'all {len(df) * len(df.columns)} cells match Excel', not diffs, diffs[:3])

# ---------- 2. Formats ----------
fmt = {'BookingNo': r'^DDBOOKING/\d{7}-\d{2}$', 'ApplicationNo': r'^DDFAPP/\d{7}-\d{2}$',
       'UnitCode': r'^T-08/(\d{4}[A-Z]?|0G\d{2})$', 'MobileNo1': r'^\d{10}$', 'MobileNo2': r'^\d{10}$', 'STATUS': r'^(Active|Cancel)$'}
for col, rx in fmt.items():
    bad = [r[col] for r in db if r[col] and not re.match(rx, r[col])]
    check(f'format {col}', not bad, bad[:3])
check('BookingNo unique', len({r['BookingNo'] for r in db}) == 133)
check('no leading/trailing whitespace', not [k for r in db for k, v in r.items() if v != v.strip()])
check('no CR characters in text', not [k for r in db for k, v in r.items() if '\r' in v])
check('dates are real dates 2020-2027', all('2020-01-01' <= r[d] <= '2027-12-31' for r in db for d in DATES if r[d]))
check('Cancel rows have CancelDate, Active do not', all((r['STATUS'] == 'Cancel') == bool(r['CancelDate']) for r in db))
check('no Excel serial numbers left in dates', not [r[d] for r in db for d in DATES if re.match(r'^\d{5}(\.0)?$', r[d])])
tot = q('SELECT SUM(TotalOutstandingWithtTax) AS o, SUM(TotalPaidWithtTax) AS p FROM housing_data')[0]
check('totals match Excel', abs(Decimal(tot['o']) - Decimal(str(round(df.TotalOutstandingWithtTax.sum(), 2)))) < Decimal('0.01')
      and abs(Decimal(tot['p']) - Decimal(str(round(df.TotalPaidWithtTax.sum(), 2)))) < Decimal('0.01'), tot)

# ---------- 3. sam_agent permissions ----------
rc, out = agent("SELECT TOP (5) BookingNo, UnitCode, STATUS FROM housing_data WHERE UnitCode = N'T-08/0303' AND (MobileNo1 = N'9919819245' OR MobileNo2 = N'9919819245');")
check('agent: verify query', rc == 0 and 'DDBOOKING/0008723-24|T-08/0303|Active' in out, out)
rc, out = agent("SELECT TotalOutstandingWithtTax FROM housing_data WHERE BookingNo = N'DDBOOKING/0008723-24';")
check('agent: balance query', rc == 0 and out == '7588791.00', out)
rc, out = agent("SELECT [001_Unit_Charge_BalanceAmount] FROM housing_data WHERE BookingNo = N'DDBOOKING/0008723-24';")
check('agent: bracketed charge column', rc == 0, out)
for col in ['PanNo', 'AAdharNo', 'Co_Applicant_PAN', 'Co_Applicant_AdharNo']:
    rc, out = agent(f'SELECT TOP (1) {col} FROM housing_data;')
    check(f'agent: {col} denied', rc != 0 and 'denied' in out, out)
for sql in ['SELECT TOP (1) * FROM housing_data;', "UPDATE housing_data SET STATUS = 'x';", 'DELETE FROM housing_data;',
            "INSERT INTO service_requests (booking_no, category, subject) VALUES ('x', 'GENERAL', 'x');",
            'SELECT TOP (1) * FROM api_request_log;', 'DROP TABLE housing_data;', 'CREATE TABLE t (i INT);']:
    rc, out = agent(sql)
    check(f'agent blocked: {sql[:40]}', rc != 0, out)
rc, out = agent("SELECT TOP (1) id FROM service_requests;")
check('agent: can read service_requests', rc == 0, out)

# ---------- 4. Procedure ----------
rc, out = agent("EXEC raise_service_request @booking_no = N'DDBOOKING/0008723-24', @caller_phone = N'9919819245', @category = N'PAYMENT_UPDATE', @subject = N'Check', @details = N'It''s a test';")
check('proc: logs request -> SR-00001', rc == 0 and out.startswith('1|SR-00001'), out)
rc, out = agent("EXEC raise_service_request @booking_no = N'NOPE', @caller_phone = N'1', @category = N'GENERAL', @subject = N'x';")
check('proc: unknown booking rejected', out.startswith('0|') and 'Booking not found' in out, out)
rc, out = agent("EXEC raise_service_request @booking_no = N'DDBOOKING/0008723-24', @caller_phone = N'1', @category = N'BAD', @subject = N'x';")
check('proc: bad category rejected', out.startswith('0|') and 'Invalid category' in out, out)
row = q('SELECT booking_no, unit_code, customer_name, caller_phone, category, details, status FROM service_requests')
check('proc: row stored with unit + name filled', len(row) == 1 and row[0]['unit_code'] == 'T-08/0303' and row[0]['details'] == "It's a test" and row[0]['status'] == 'OPEN', row)
q('TRUNCATE TABLE service_requests')

# ---------- 5. Dashboard / API ----------
check('API /health', json.load(u.urlopen('http://127.0.0.1:8000/health'))['status'] == 'healthy')
check('UI page loads', u.urlopen('http://127.0.0.1:8000/').status == 200)
check('runner: unnamed column', q('SELECT COUNT(*) FROM housing_data') == [{'col1': '133'}])
check("runner: LIKE '%..%'", int(q("SELECT COUNT(*) AS n FROM housing_data WHERE BookingRemarks LIKE N'%RERA%'")[0]['n']) > 0)
check('call log endpoint', isinstance(json.load(u.urlopen('http://127.0.0.1:8000/admin/logs?limit=5')), list))
doc = open('tests/TEST_CASES.md', encoding='utf-8').read()
logq = doc.split('**Agent query log** —')[1].split('```sql\n')[1].split('\n```')[0]
import time; time.sleep(3)
log = q(logq)
check('agent query log shows agent SQL + errors', any('DDBOOKING/0008723-24' in r['sql_text'] for r in log)
      and any(r['event'] == 'error_reported' for r in log), len(log))

# ---------- 6. Every SQL block in TEST_CASES.md runs ----------
blocks = re.findall(r'```sql\n(.*?)\n```', doc, re.S)
failed = []
for b in blocks:
    sql = b.replace('<UNIT>', 'T-08/0303').replace('<MOBILE>', '9919819245')
    try:
        q(sql)
    except Exception as e:
        failed.append((sql[:60], str(e)[:120]))
check(f'all {len(blocks)} SQL blocks in TEST_CASES.md run', not failed, failed)

print(f'\n{sum(results)}/{len(results)} passed')
raise SystemExit(0 if all(results) else 1)
