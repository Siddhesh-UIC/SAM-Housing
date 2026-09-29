"""Build db/init/01_schema.sql from the CRM Excel export (single table housing_data)."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
df = pd.read_excel(ROOT / 'CRM Data_Solace_Anuj Version_DummyV2.xlsx')

DATE_COLS = {'BookingDate', 'ApplicationDate', 'Agreementdate', 'Allotmentdate', 'CancelDate',
             'AgreementRegistrationDate'}
# Numeric in Excel but really identifiers: keep as text so leading zeros / formatting survive.
ID_COLS = {'AAdharNo', 'MobileNo1', 'MobileNo2', 'Co_Applicant_AdharNo', 'Bookingid',
           'AgreementRegistrationNo'}
# Never exposed to the agent (column-level grant below skips them).
PII_COLS = {'AAdharNo', 'Co_Applicant_AdharNo', 'PanNo', 'Co_Applicant_PAN'}


def col_type(c):
    if c in DATE_COLS:
        return 'DATE'
    if c in ID_COLS:
        return 'VARCHAR(50)'
    if pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().any():
        return 'DECIMAL(15,2)'
    return 'TEXT' if c == 'BookingRemarks' else 'VARCHAR(255)'


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
    s = str(v).strip().replace('\\', '\\\\').replace("'", "\\'")
    return f"'{s}'"


names = {c: c.replace(' ', '_').replace('.', '_').replace('-', '_') for c in df.columns}
out = ['DROP DATABASE IF EXISTS housing;', 'CREATE DATABASE housing;', 'USE housing;', '',
       'CREATE TABLE housing_data (', '    id INT AUTO_INCREMENT PRIMARY KEY,']
out += [f'    `{names[c]}` {col_type(c)},' for c in df.columns]
out[-1] = out[-1].rstrip(',')
out += [');', '']

col_list = ', '.join(f'`{names[c]}`' for c in df.columns)
for _, row in df.iterrows():
    out.append(f"INSERT INTO housing_data ({col_list}) VALUES "
               f"({', '.join(sql_val(c, row[c]) for c in df.columns)});")

out.append("""
CREATE TABLE service_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    booking_no VARCHAR(255) NOT NULL,
    unit_code VARCHAR(255),
    customer_name VARCHAR(255),
    caller_phone VARCHAR(20),
    category VARCHAR(30) NOT NULL,
    subject VARCHAR(300) NOT NULL,
    details TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN'
);

CREATE TABLE api_request_log (id BIGINT AUTO_INCREMENT PRIMARY KEY, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, method VARCHAR(10) NOT NULL, path VARCHAR(500) NOT NULL, detail TEXT, status INT NOT NULL, duration_ms DECIMAL(10,1) NOT NULL);

DELIMITER //
-- The agent's only write path: logs a request for the back office and returns its reference.
CREATE PROCEDURE raise_service_request(IN p_booking_no VARCHAR(255), IN p_caller_phone VARCHAR(20),
    IN p_category VARCHAR(30), IN p_subject VARCHAR(300), IN p_details TEXT)
SQL SECURITY DEFINER
BEGIN
    DECLARE v_unit VARCHAR(255);
    DECLARE v_name VARCHAR(255);
    SELECT UnitCode, CustomerName INTO v_unit, v_name
      FROM housing_data WHERE BookingNo = p_booking_no LIMIT 1;
    IF v_unit IS NULL THEN
        SELECT FALSE AS success, NULL AS request_ref, 'Booking not found' AS message;
    ELSEIF p_category NOT IN ('PAYMENT_UPDATE','TDS_UPDATE','DOCUMENT_REQUEST','SALE_DEED_DELAY',
                              'HANDOVER_INQUIRY','REGISTRY_SCHEDULE','GENERAL') THEN
        SELECT FALSE AS success, NULL AS request_ref, 'Invalid category' AS message;
    ELSE
        INSERT INTO service_requests (booking_no, unit_code, customer_name, caller_phone, category, subject, details)
        VALUES (p_booking_no, v_unit, v_name, p_caller_phone, p_category, p_subject, p_details);
        SELECT TRUE AS success, CONCAT('SR-', LPAD(LAST_INSERT_ID(), 5, '0')) AS request_ref,
               'Request logged for the CRM team' AS message;
    END IF;
END //
DELIMITER ;
""")

agent_cols = ', '.join(f'`{names[c]}`' for c in df.columns if c not in PII_COLS)
out += ["CREATE USER IF NOT EXISTS 'sam_agent'@'%' IDENTIFIED BY 'sam_agent123';",
        f"GRANT SELECT (id, {agent_cols}) ON housing.housing_data TO 'sam_agent'@'%';",
        "GRANT SELECT ON housing.service_requests TO 'sam_agent'@'%';",
        "GRANT EXECUTE ON PROCEDURE housing.raise_service_request TO 'sam_agent'@'%';",
        "FLUSH PRIVILEGES;", '']

(ROOT / 'db/init/01_schema.sql').write_text('\n'.join(out), encoding='utf-8')
print(f'Done generating {len(df.columns)} columns and {len(df)} rows.')
