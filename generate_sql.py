"""Build db/init/01_schema.sql (T-SQL for Microsoft SQL Server) from the CRM Excel export."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
df = pd.read_excel(ROOT / 'CRM Data_Solace_Anuj Version_DummyV2.xlsx')

DATE_COLS = {'BookingDate', 'ApplicationDate', 'Agreementdate', 'Allotmentdate', 'CancelDate',
             'AgreementRegistrationDate'}
# Numeric in Excel but really identifiers: keep as text so leading zeros / formatting survive.
ID_COLS = {'AAdharNo', 'MobileNo1', 'MobileNo2', 'Co_Applicant_AdharNo', 'Bookingid',
           'AgreementRegistrationNo'}
# Never exposed to the agent (DENY below).
PII_COLS = ['AAdharNo', 'Co_Applicant_AdharNo', 'PanNo', 'Co_Applicant_PAN']


def col_type(c):
    if c in DATE_COLS:
        return 'DATE'
    if c in ID_COLS:
        return 'NVARCHAR(50)'
    if pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().any():
        return 'DECIMAL(15,2)'
    return 'NVARCHAR(MAX)' if c == 'BookingRemarks' else 'NVARCHAR(255)'


def to_date(v):
    if isinstance(v, (int, float)):
        return pd.Timestamp('1899-12-30') + pd.Timedelta(days=v)  # Excel serial date
    return pd.Timestamp(v)


def sql_val(c, v):
    if pd.isna(v) or (isinstance(v, str) and not v.strip()):
        return 'NULL'
    if c in DATE_COLS:
        return f"'{to_date(v):%Y-%m-%d}'"
    if c in ID_COLS:
        v = str(int(v)) if isinstance(v, float) else str(v)
    elif col_type(c) == 'DECIMAL(15,2)':
        return str(v)
    return "N'" + str(v).strip().replace("'", "''") + "'"


names = {c: c.replace(' ', '_').replace('.', '_').replace('-', '_') for c in df.columns}
out = ["IF DB_ID('housing') IS NOT NULL BEGIN ALTER DATABASE housing SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE housing; END",
       'GO', 'CREATE DATABASE housing;', 'GO', 'USE housing;', 'GO', '',
       'CREATE TABLE housing_data (', '    id INT IDENTITY(1,1) PRIMARY KEY,']
out += [f'    [{names[c]}] {col_type(c)},' for c in df.columns]
out[-1] = out[-1].rstrip(',')
out += [');', 'GO', 'SET NOCOUNT ON;']

col_list = ', '.join(f'[{names[c]}]' for c in df.columns)
for _, row in df.iterrows():
    out.append(f"INSERT INTO housing_data ({col_list}) VALUES "
               f"({', '.join(sql_val(c, row[c]) for c in df.columns)});")
out.append('GO')

pii = ', '.join(f'[{c}]' for c in PII_COLS)
out.append(f"""
CREATE TABLE service_requests (
    id INT IDENTITY(1,1) PRIMARY KEY,
    created_at DATETIME2(0) NOT NULL DEFAULT SYSDATETIME(),
    booking_no NVARCHAR(255) NOT NULL,
    unit_code NVARCHAR(255),
    customer_name NVARCHAR(255),
    caller_phone NVARCHAR(20),
    category NVARCHAR(30) NOT NULL,
    subject NVARCHAR(300) NOT NULL,
    details NVARCHAR(MAX),
    status NVARCHAR(20) NOT NULL DEFAULT 'OPEN'
);

CREATE TABLE api_request_log (id BIGINT IDENTITY(1,1) PRIMARY KEY, created_at DATETIME2(0) NOT NULL DEFAULT SYSDATETIME(), method NVARCHAR(10) NOT NULL, path NVARCHAR(500) NOT NULL, detail NVARCHAR(MAX), status INT NOT NULL, duration_ms DECIMAL(10,1) NOT NULL);
GO

-- The agent's only write path: logs a request for the back office and returns its reference.
-- Runs with the owner's rights via ownership chaining, so sam_agent needs EXECUTE only.
CREATE PROCEDURE raise_service_request
    @booking_no NVARCHAR(255), @caller_phone NVARCHAR(20), @category NVARCHAR(30),
    @subject NVARCHAR(300), @details NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @unit NVARCHAR(255), @name NVARCHAR(255), @id INT;
    SELECT TOP (1) @unit = UnitCode, @name = CustomerName FROM housing_data WHERE BookingNo = @booking_no;
    IF @unit IS NULL
        SELECT CAST(0 AS BIT) AS success, CAST(NULL AS NVARCHAR(20)) AS request_ref, N'Booking not found' AS message;
    ELSE IF @category NOT IN ('PAYMENT_UPDATE','TDS_UPDATE','DOCUMENT_REQUEST','SALE_DEED_DELAY',
                              'HANDOVER_INQUIRY','REGISTRY_SCHEDULE','GENERAL')
        SELECT CAST(0 AS BIT) AS success, CAST(NULL AS NVARCHAR(20)) AS request_ref, N'Invalid category' AS message;
    ELSE
    BEGIN
        INSERT INTO service_requests (booking_no, unit_code, customer_name, caller_phone, category, subject, details)
        VALUES (@booking_no, @unit, @name, @caller_phone, @category, @subject, @details);
        SET @id = SCOPE_IDENTITY();
        SELECT CAST(1 AS BIT) AS success, 'SR-' + RIGHT('00000' + CAST(@id AS VARCHAR(10)), 5) AS request_ref,
               N'Request logged for the CRM team' AS message;
    END
END
GO

-- Demo logins: CHECK_POLICY OFF keeps the simple demo passwords.
IF SUSER_ID('housing') IS NULL CREATE LOGIN housing WITH PASSWORD = 'housing123', CHECK_POLICY = OFF;
IF SUSER_ID('sam_agent') IS NULL CREATE LOGIN sam_agent WITH PASSWORD = 'sam_agent123', CHECK_POLICY = OFF, DEFAULT_DATABASE = housing;
GO
CREATE USER housing FOR LOGIN housing;
ALTER ROLE db_owner ADD MEMBER housing;
CREATE USER sam_agent FOR LOGIN sam_agent;
GRANT SELECT ON housing_data TO sam_agent;
DENY SELECT ON housing_data ({pii}) TO sam_agent;
GRANT SELECT ON service_requests TO sam_agent;
GRANT EXECUTE ON raise_service_request TO sam_agent;
GO
-- Lets the dashboard (runs as housing) read the agent query trace below.
USE master;
GRANT VIEW SERVER STATE TO housing;
GO

-- Records every statement sam_agent runs (the SQL Server equivalent of MySQL's general log).
IF EXISTS (SELECT 1 FROM sys.server_event_sessions WHERE name = 'agent_queries') DROP EVENT SESSION agent_queries ON SERVER;
GO
CREATE EVENT SESSION agent_queries ON SERVER
ADD EVENT sqlserver.sql_batch_completed (ACTION (sqlserver.username) WHERE sqlserver.username = N'sam_agent'),
ADD EVENT sqlserver.rpc_completed (ACTION (sqlserver.username) WHERE sqlserver.username = N'sam_agent'),
ADD EVENT sqlserver.error_reported (ACTION (sqlserver.username, sqlserver.sql_text)
    WHERE sqlserver.username = N'sam_agent' AND severity > 10)
ADD TARGET package0.event_file (SET filename = N'/var/opt/mssql/log/agent_queries.xel', max_file_size = 20)
WITH (STARTUP_STATE = ON, MAX_DISPATCH_LATENCY = 1 SECONDS);  -- visible in the log within ~1 s
GO
ALTER EVENT SESSION agent_queries ON SERVER STATE = START;
GO
""")

# newline='\n': on Windows the default would turn line breaks inside remarks into \r\n.
(ROOT / 'db/init/01_schema.sql').write_text('\n'.join(out), encoding='utf-8', newline='\n')
print(f'Done generating {len(df.columns)} columns and {len(df)} rows.')
