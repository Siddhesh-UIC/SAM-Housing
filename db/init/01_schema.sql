-- Mock housing CRM schema for the SAM Housing PoC.
-- Covers: payment ledger, TDS, documents, cases, handover, registry scheduling.

-- ── Base tables ─────────────────────────────────────────────────────────────

CREATE TABLE projects (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    code        VARCHAR(20) UNIQUE NOT NULL,
    name        VARCHAR(200) NOT NULL,
    developer   VARCHAR(200) NOT NULL,
    location    VARCHAR(200) NOT NULL,
    city        VARCHAR(100) NOT NULL,
    state       VARCHAR(100) NOT NULL,
    rera_no     VARCHAR(50),
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE units (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    project_id  INT NOT NULL,
    unit_no     VARCHAR(50) NOT NULL,
    unit_type   ENUM('FLAT','PLOT','VILLA','SHOP') NOT NULL,
    block       VARCHAR(20),
    floor_no    INT,
    area_sqft   DECIMAL(10,2) NOT NULL,
    base_price  DECIMAL(15,2) NOT NULL,
    status      ENUM('AVAILABLE','BOOKED','SOLD','HANDEDOVER') NOT NULL DEFAULT 'AVAILABLE',
    UNIQUE KEY (project_id, unit_no),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE customers (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    customer_id  VARCHAR(20) UNIQUE NOT NULL,          -- CRM customer ref
    full_name    VARCHAR(200) NOT NULL,
    phone        VARCHAR(20) UNIQUE NOT NULL,           -- caller ID
    email        VARCHAR(200),
    pan          VARCHAR(10),
    aadhaar_hash VARCHAR(64),                           -- SHA-256 of Aadhaar, never exposed
    city         VARCHAR(100),
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bookings (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    booking_ref     VARCHAR(30) UNIQUE NOT NULL,
    customer_id     INT NOT NULL,
    unit_id         INT NOT NULL,
    booking_date    DATE NOT NULL,
    agreement_value DECIMAL(15,2) NOT NULL,
    payment_plan    ENUM('CLP','TLP','FLEXI','POSSESSION') NOT NULL DEFAULT 'CLP',
    status          ENUM('ACTIVE','CANCELLED','COMPLETED') NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE
);

CREATE TABLE payments (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    booking_id    INT NOT NULL,
    amount        DECIMAL(15,2) NOT NULL,
    payment_date  DATE NOT NULL,
    payment_mode  ENUM('CHEQUE','NEFT','RTGS','UPI','CASH','DD') NOT NULL,
    receipt_no    VARCHAR(50),
    tds_deducted  DECIMAL(15,2) NOT NULL DEFAULT 0,
    remarks       VARCHAR(500),
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
);

CREATE TABLE documents (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    booking_id    INT NOT NULL,
    doc_type      ENUM('AFS','SALE_DEED','FORM_132','POSSESSION_LETTER','NOC','ALLOTMENT_LETTER') NOT NULL,
    doc_ref       VARCHAR(100),
    status        ENUM('PENDING','ISSUED','SUBMITTED','DISPATCHED','RECEIVED') NOT NULL DEFAULT 'PENDING',
    issued_at     TIMESTAMP NULL,
    dispatched_at TIMESTAMP NULL,
    remarks       VARCHAR(500),
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
);

CREATE TABLE tds_records (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    booking_id      INT NOT NULL,
    financial_year  VARCHAR(10) NOT NULL,               -- e.g. 2025-26
    amount          DECIMAL(15,2) NOT NULL,
    certificate_no  VARCHAR(50),
    status          ENUM('PENDING','SUBMITTED','VERIFIED','REJECTED') NOT NULL DEFAULT 'PENDING',
    submitted_at    TIMESTAMP NULL,
    remarks         VARCHAR(500),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
);

CREATE TABLE cases (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    case_ref      VARCHAR(30) UNIQUE NOT NULL,
    customer_id   INT NOT NULL,
    booking_id    INT,
    category      ENUM('PAYMENT_UPDATE','TDS_UPDATE','DOCUMENT_REQUEST','SALE_DEED_DELAY',
                       'HANDOVER_INQUIRY','REGISTRY_SCHEDULE','GENERAL') NOT NULL,
    subject       VARCHAR(300) NOT NULL,
    description   TEXT,
    status        ENUM('OPEN','IN_PROGRESS','RESOLVED','CLOSED','ESCALATED') NOT NULL DEFAULT 'OPEN',
    priority      ENUM('LOW','MEDIUM','HIGH','URGENT') NOT NULL DEFAULT 'MEDIUM',
    assigned_to   VARCHAR(100),
    resolved_at   TIMESTAMP NULL,
    resolution    TEXT,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE SET NULL
);

CREATE TABLE case_comments (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    case_id     INT NOT NULL,
    author      VARCHAR(100) NOT NULL DEFAULT 'SYSTEM',
    comment     TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
);

-- Agent API call log (PINs / sensitive data masked before insert).
CREATE TABLE api_request_log (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    method      VARCHAR(10) NOT NULL,
    path        VARCHAR(500) NOT NULL,
    detail      TEXT,
    status      INT NOT NULL,
    duration_ms DECIMAL(10,1) NOT NULL
);


-- ── Agent-facing views (never expose PAN / Aadhaar) ─────────────────────────

CREATE OR REPLACE VIEW customer_bookings AS
SELECT c.customer_id, c.full_name, c.phone, c.email, c.city AS customer_city,
       b.id AS booking_id, b.booking_ref, b.booking_date, b.agreement_value,
       b.payment_plan, b.status AS booking_status,
       u.unit_no, u.unit_type, u.block, u.floor_no, u.area_sqft, u.status AS unit_status,
       p.code AS project_code, p.name AS project_name, p.location AS project_location, p.city AS project_city
FROM customers c
JOIN bookings b ON b.customer_id = c.id
JOIN units u    ON u.id = b.unit_id
JOIN projects p ON p.id = u.project_id;

CREATE OR REPLACE VIEW booking_payments AS
SELECT c.customer_id, c.full_name, c.phone,
       b.booking_ref, b.agreement_value,
       pay.id AS payment_id, pay.amount, pay.payment_date, pay.payment_mode,
       pay.receipt_no, pay.tds_deducted, pay.remarks
FROM payments pay
JOIN bookings b  ON b.id = pay.booking_id
JOIN customers c ON c.id = b.customer_id;

CREATE OR REPLACE VIEW booking_documents AS
SELECT c.customer_id, c.full_name, c.phone,
       b.booking_ref,
       d.id AS document_id, d.doc_type, d.doc_ref, d.status AS doc_status,
       d.issued_at, d.dispatched_at, d.remarks
FROM documents d
JOIN bookings b  ON b.id = d.booking_id
JOIN customers c ON c.id = b.customer_id;

CREATE OR REPLACE VIEW customer_cases AS
SELECT c.customer_id, c.full_name, c.phone,
       cs.id AS case_id, cs.case_ref, cs.category, cs.subject, cs.description,
       cs.status AS case_status, cs.priority, cs.assigned_to,
       cs.resolved_at, cs.resolution, cs.created_at,
       b.booking_ref, u.unit_no, p.name AS project_name
FROM cases cs
JOIN customers c ON c.id = cs.customer_id
LEFT JOIN bookings b ON b.id = cs.booking_id
LEFT JOIN units u    ON u.id = b.unit_id
LEFT JOIN projects p ON p.id = u.project_id;

CREATE OR REPLACE VIEW booking_tds AS
SELECT c.customer_id, c.full_name, c.phone,
       b.booking_ref,
       t.id AS tds_id, t.financial_year, t.amount AS tds_amount,
       t.certificate_no, t.status AS tds_status, t.submitted_at, t.remarks
FROM tds_records t
JOIN bookings b  ON b.id = t.booking_id
JOIN customers c ON c.id = b.customer_id;


-- ── Stored procedures ───────────────────────────────────────────────────────

DELIMITER //

CREATE PROCEDURE get_payment_summary(IN p_phone VARCHAR(20), IN p_booking_ref VARCHAR(30))
BEGIN
    DECLARE v_booking_id INT;
    DECLARE v_agreement DECIMAL(15,2);
    DECLARE v_total_paid DECIMAL(15,2) DEFAULT 0;
    DECLARE v_total_tds DECIMAL(15,2) DEFAULT 0;

    SELECT b.id, b.agreement_value INTO v_booking_id, v_agreement
    FROM bookings b JOIN customers c ON c.id = b.customer_id
    WHERE c.phone = p_phone AND b.booking_ref = p_booking_ref
    LIMIT 1;

    IF v_booking_id IS NULL THEN
        SELECT FALSE AS success, 'BOOKING_NOT_FOUND' AS message,
               NULL AS agreement_value, NULL AS total_paid,
               NULL AS total_tds, NULL AS balance_due;
    ELSE
        SELECT COALESCE(SUM(amount), 0), COALESCE(SUM(tds_deducted), 0)
        INTO v_total_paid, v_total_tds
        FROM payments WHERE booking_id = v_booking_id;

        SELECT TRUE AS success, 'OK' AS message,
               v_agreement AS agreement_value, v_total_paid AS total_paid,
               v_total_tds AS total_tds,
               (v_agreement - v_total_paid) AS balance_due;
    END IF;
END //

CREATE PROCEDURE raise_case(
    IN p_phone VARCHAR(20),
    IN p_booking_ref VARCHAR(30),
    IN p_category VARCHAR(30),
    IN p_subject VARCHAR(300),
    IN p_description TEXT
)
BEGIN
    DECLARE v_cust_id INT;
    DECLARE v_booking_id INT DEFAULT NULL;
    DECLARE v_ref VARCHAR(30);

    SELECT id INTO v_cust_id FROM customers WHERE phone = p_phone LIMIT 1;
    IF v_cust_id IS NULL THEN
        SELECT FALSE AS success, NULL AS case_ref, 'CUSTOMER_NOT_FOUND' AS message;
    ELSE
        IF p_booking_ref IS NOT NULL AND p_booking_ref != '' THEN
            SELECT b.id INTO v_booking_id
            FROM bookings b WHERE b.booking_ref = p_booking_ref AND b.customer_id = v_cust_id
            LIMIT 1;
            IF v_booking_id IS NULL THEN
                SELECT FALSE AS success, NULL AS case_ref, 'BOOKING_NOT_FOUND' AS message;
                -- early return via LEAVE not needed; the IF/ELSE handles it
            END IF;
        END IF;

        IF v_cust_id IS NOT NULL AND (p_booking_ref IS NULL OR p_booking_ref = '' OR v_booking_id IS NOT NULL) THEN
            SET v_ref = CONCAT('CASE-', DATE_FORMAT(NOW(), '%Y%m%d'), '-',
                               UPPER(SUBSTRING(MD5(RAND()), 1, 6)));
            INSERT INTO cases (case_ref, customer_id, booking_id, category, subject, description)
            VALUES (v_ref, v_cust_id, v_booking_id, p_category, p_subject, p_description);

            INSERT INTO case_comments (case_id, author, comment)
            VALUES (LAST_INSERT_ID(), 'SYSTEM', CONCAT('Case raised: ', p_subject));

            SELECT TRUE AS success, v_ref AS case_ref, 'CASE_CREATED' AS message;
        END IF;
    END IF;
END //

DELIMITER ;


-- ── Least-privilege role for the SAM MySQL connector ────────────────────────
-- Can read the views and call stored procedures; cannot touch base tables.

CREATE USER IF NOT EXISTS 'sam_agent'@'%' IDENTIFIED BY 'sam_agent123';
GRANT SELECT ON housing.customer_bookings  TO 'sam_agent'@'%';
GRANT SELECT ON housing.booking_payments   TO 'sam_agent'@'%';
GRANT SELECT ON housing.booking_documents  TO 'sam_agent'@'%';
GRANT SELECT ON housing.customer_cases     TO 'sam_agent'@'%';
GRANT SELECT ON housing.booking_tds        TO 'sam_agent'@'%';
GRANT EXECUTE ON PROCEDURE housing.get_payment_summary TO 'sam_agent'@'%';
GRANT EXECUTE ON PROCEDURE housing.raise_case          TO 'sam_agent'@'%';
FLUSH PRIVILEGES;
