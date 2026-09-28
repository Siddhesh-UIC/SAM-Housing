-- Demo data for SAM Housing. All names, numbers and details are fictional test data.

-- ── Projects ────────────────────────────────────────────────────────────────

INSERT INTO projects (code, name, developer, location, city, state, rera_no) VALUES
('HGH', 'Hero Gharaunda',   'Hero Realty Pvt Ltd',  'Gharaunda, NH-44',        'Haridwar',   'Uttarakhand', 'RERA-UK-2023-0042'),
('HHL', 'Hero Homes',       'Hero Homes Pvt Ltd',   'Sector 88, Sahibzada Ajit Singh Nagar', 'Ludhiana',   'Punjab',       'RERA-PB-2022-0187'),
('HGN', 'Hero Green Valley','Hero Realty Pvt Ltd',   'Sector 12, Dwarka Expressway',          'Gurugram',   'Haryana',      'RERA-HR-2024-0301');

-- ── Units ───────────────────────────────────────────────────────────────────

INSERT INTO units (project_id, unit_no, unit_type, block, floor_no, area_sqft, base_price, status) VALUES
-- Hero Gharaunda (flats)
(1, 'B-2/202',  'FLAT', 'B-2', 2, 1250.00, 4500000.00,  'SOLD'),
(1, 'B-2/203',  'FLAT', 'B-2', 2, 1250.00, 4500000.00,  'SOLD'),
(1, 'A-1/501',  'FLAT', 'A-1', 5, 1450.00, 5200000.00,  'BOOKED'),
(1, 'C-3/101',  'FLAT', 'C-3', 1, 950.00,  3400000.00,  'AVAILABLE'),
-- Hero Gharaunda (plots)
(1, 'R-109',    'PLOT', NULL,  NULL, 2400.00, 3600000.00, 'SOLD'),
(1, 'R-215',    'PLOT', NULL,  NULL, 1800.00, 2700000.00, 'BOOKED'),
-- Hero Homes Ludhiana
(2, 'T05-2501', 'FLAT', 'T05', 25, 1650.00, 7800000.00,  'SOLD'),
(2, 'T03-1201', 'FLAT', 'T03', 12, 1350.00, 6200000.00,  'BOOKED'),
(2, 'T07-0801', 'FLAT', 'T07', 8,  1100.00, 5100000.00,  'AVAILABLE'),
-- Hero Green Valley
(3, 'GV-A/301', 'FLAT', 'GV-A', 3, 1550.00, 8500000.00, 'BOOKED'),
(3, 'GV-B/102', 'VILLA', 'GV-B', 1, 2800.00, 15000000.00, 'SOLD'),
(3, 'GV-C/405', 'FLAT', 'GV-C', 4, 1200.00, 6600000.00, 'AVAILABLE');

-- ── Customers ───────────────────────────────────────────────────────────────

INSERT INTO customers (customer_id, full_name, phone, email, pan, city) VALUES
('CUST0001', 'Rajesh Kumar Sharma',   '+919876543201', 'rajesh.sharma@example.com',    'ABCDS1234F', 'Haridwar'),
('CUST0002', 'Priya Verma',           '+919876543202', 'priya.verma@example.com',      'BCDPV2345G', 'Haridwar'),
('CUST0003', 'Amit Gupta',            '+919876543203', 'amit.gupta@example.com',       'CDEAG3456H', 'Delhi'),
('CUST0004', 'Sunita Devi',           '+919876543204', 'sunita.devi@example.com',      'DEFSD4567J', 'Ludhiana'),
('CUST0005', 'Vikram Singh Rathore',  '+919876543205', 'vikram.rathore@example.com',   'EFGVR5678K', 'Ludhiana'),
('CUST0006', 'Neha Agarwal',          '+919876543206', 'neha.agarwal@example.com',     'FGHNA6789L', 'Gurugram'),
('CUST0007', 'Manoj Kumar Yadav',     '+919876543207', 'manoj.yadav@example.com',      'GHIMY7890M', 'Chandigarh'),
('CUST0008', 'Kavita Joshi',          '+919876543208', 'kavita.joshi@example.com',     'HIJKJ8901N', 'Dehradun');

-- ── Bookings ────────────────────────────────────────────────────────────────

INSERT INTO bookings (booking_ref, customer_id, unit_id, booking_date, agreement_value, payment_plan, status) VALUES
('BK-2023-001', 1, 1,  '2023-03-15', 4500000.00,  'CLP',        'ACTIVE'),       -- Rajesh → B-2/202 Gharaunda
('BK-2023-002', 1, 2,  '2023-03-15', 4500000.00,  'CLP',        'ACTIVE'),       -- Rajesh → B-2/203 Gharaunda (same customer, 2 flats)
('BK-2023-003', 2, 5,  '2023-06-10', 3600000.00,  'TLP',        'ACTIVE'),       -- Priya → R-109 plot
('BK-2023-004', 3, 3,  '2023-09-20', 5200000.00,  'CLP',        'ACTIVE'),       -- Amit → A-1/501
('BK-2024-005', 4, 7,  '2024-01-05', 7800000.00,  'FLEXI',      'ACTIVE'),       -- Sunita → T05-2501
('BK-2024-006', 5, 8,  '2024-04-12', 6200000.00,  'CLP',        'ACTIVE'),       -- Vikram → T03-1201
('BK-2024-007', 6, 10, '2024-07-01', 8500000.00,  'POSSESSION', 'ACTIVE'),       -- Neha → GV-A/301
('BK-2024-008', 7, 6,  '2024-02-20', 2700000.00,  'TLP',        'ACTIVE'),       -- Manoj → R-215 plot
('BK-2025-009', 8, 11, '2025-01-10', 15000000.00, 'CLP',        'ACTIVE'),       -- Kavita → GV-B/102 villa
('BK-2023-010', 3, 6,  '2023-11-01', 2700000.00,  'TLP',        'CANCELLED');    -- Amit had another booking, cancelled

-- ── Payments ────────────────────────────────────────────────────────────────

INSERT INTO payments (booking_id, amount, payment_date, payment_mode, receipt_no, tds_deducted, remarks) VALUES
-- Rajesh - B-2/202 (BK-2023-001): almost fully paid
(1, 450000.00,  '2023-03-15', 'CHEQUE', 'RCP-001-A', 0,         'Booking amount'),
(1, 900000.00,  '2023-06-01', 'NEFT',   'RCP-001-B', 45000.00,  'First installment'),
(1, 900000.00,  '2023-09-01', 'NEFT',   'RCP-001-C', 45000.00,  'Second installment'),
(1, 900000.00,  '2023-12-01', 'RTGS',   'RCP-001-D', 45000.00,  'Third installment'),
(1, 900000.00,  '2024-03-01', 'NEFT',   'RCP-001-E', 45000.00,  'Fourth installment'),
-- Rajesh - B-2/203 (BK-2023-002): partially paid
(2, 450000.00,  '2023-03-15', 'CHEQUE', 'RCP-002-A', 0,         'Booking amount'),
(2, 900000.00,  '2023-07-01', 'NEFT',   'RCP-002-B', 45000.00,  'First installment'),
(2, 900000.00,  '2024-01-01', 'RTGS',   'RCP-002-C', 45000.00,  'Second installment'),
-- Priya - R-109 plot (BK-2023-003): under 50 lakh, no TDS required
(3, 360000.00,  '2023-06-10', 'CHEQUE', 'RCP-003-A', 0,         'Booking amount'),
(3, 1200000.00, '2023-09-15', 'NEFT',   'RCP-003-B', 0,         'First installment - TDS not applicable (under 50L)'),
(3, 1200000.00, '2024-01-15', 'NEFT',   'RCP-003-C', 0,         'Second installment'),
(3, 840000.00,  '2024-06-15', 'UPI',    'RCP-003-D', 0,         'Final installment'),
-- Amit - A-1/501 (BK-2023-004)
(4, 520000.00,  '2023-09-20', 'DD',     'RCP-004-A', 0,         'Booking amount'),
(4, 1200000.00, '2024-01-01', 'NEFT',   'RCP-004-B', 60000.00,  'First installment'),
(4, 1200000.00, '2024-06-01', 'RTGS',   'RCP-004-C', 60000.00,  'Second installment'),
-- Sunita - T05-2501 (BK-2024-005)
(5, 780000.00,  '2024-01-05', 'CHEQUE', 'RCP-005-A', 0,         'Booking amount'),
(5, 2000000.00, '2024-04-01', 'NEFT',   'RCP-005-B', 100000.00, 'First installment'),
(5, 2000000.00, '2024-08-01', 'RTGS',   'RCP-005-C', 100000.00, 'Second installment'),
(5, 1500000.00, '2025-01-01', 'NEFT',   'RCP-005-D', 75000.00,  'Third installment'),
-- Vikram - T03-1201 (BK-2024-006)
(6, 620000.00,  '2024-04-12', 'CHEQUE', 'RCP-006-A', 0,         'Booking amount'),
(6, 1500000.00, '2024-08-01', 'NEFT',   'RCP-006-B', 75000.00,  'First installment'),
-- Neha - GV-A/301 (BK-2024-007)
(7, 850000.00,  '2024-07-01', 'DD',     'RCP-007-A', 0,         'Booking amount'),
(7, 2500000.00, '2024-11-01', 'RTGS',   'RCP-007-B', 125000.00, 'First installment'),
-- Manoj - R-215 plot (BK-2024-008)
(8, 270000.00,  '2024-02-20', 'UPI',    'RCP-008-A', 0,         'Booking amount'),
(8, 1200000.00, '2024-06-01', 'NEFT',   'RCP-008-B', 0,         'First installment (under 50L, no TDS)'),
-- Kavita - GV-B/102 villa (BK-2025-009)
(9, 1500000.00, '2025-01-10', 'CHEQUE', 'RCP-009-A', 0,         'Booking amount'),
(9, 4000000.00, '2025-04-01', 'RTGS',   'RCP-009-B', 200000.00, 'First milestone');

-- ── Documents ───────────────────────────────────────────────────────────────

INSERT INTO documents (booking_id, doc_type, doc_ref, status, issued_at, dispatched_at, remarks) VALUES
-- Rajesh B-2/202: AFS issued, Sale Deed pending (Case 2 scenario)
(1, 'ALLOTMENT_LETTER', 'AL-2023-001', 'ISSUED',    '2023-03-20', '2023-03-22', NULL),
(1, 'AFS',              'AFS-2023-001','ISSUED',     '2023-04-10', '2023-04-12', NULL),
(1, 'SALE_DEED',         NULL,          'PENDING',    NULL,         NULL,         'Registration pending from builder side'),
-- Rajesh B-2/203: same situation
(2, 'ALLOTMENT_LETTER', 'AL-2023-002', 'ISSUED',    '2023-03-20', '2023-03-22', NULL),
(2, 'AFS',              'AFS-2023-002','ISSUED',     '2023-04-10', NULL,         'AFS ready, not yet collected'),
(2, 'SALE_DEED',         NULL,          'PENDING',    NULL,         NULL,         'Registration pending from builder side'),
-- Priya R-109: fully paid, docs complete
(3, 'ALLOTMENT_LETTER', 'AL-2023-003', 'ISSUED',    '2023-06-15', '2023-06-17', NULL),
(3, 'AFS',              'AFS-2023-003','DISPATCHED', '2023-07-01', '2023-07-03', 'Dispatched via courier'),
(3, 'SALE_DEED',        'SD-2024-003', 'ISSUED',    '2024-08-15', '2024-08-20', NULL),
-- Amit A-1/501
(4, 'ALLOTMENT_LETTER', 'AL-2023-004', 'ISSUED',    '2023-10-01', '2023-10-03', NULL),
-- Sunita T05-2501: Form 132 scenario
(5, 'ALLOTMENT_LETTER', 'AL-2024-005', 'ISSUED',    '2024-01-15', '2024-01-18', NULL),
(5, 'FORM_132',         'F132-2025-005','SUBMITTED', '2025-07-15', NULL,         'Form 132 for July 2026 payment'),
-- Kavita GV-B/102 villa
(9, 'ALLOTMENT_LETTER', 'AL-2025-009', 'ISSUED',    '2025-01-15', '2025-01-18', NULL);

-- ── TDS Records ─────────────────────────────────────────────────────────────

INSERT INTO tds_records (booking_id, financial_year, amount, certificate_no, status, submitted_at, remarks) VALUES
-- Rajesh B-2/202
(1, '2023-24', 90000.00,  'TDS-23-001', 'VERIFIED',  '2023-12-15', NULL),
(1, '2024-25', 90000.00,  'TDS-24-001', 'VERIFIED',  '2024-06-15', NULL),
-- Rajesh B-2/203
(2, '2023-24', 45000.00,  'TDS-23-002', 'SUBMITTED', '2024-01-10', NULL),
(2, '2024-25', 45000.00,  'TDS-24-002', 'SUBMITTED', '2024-07-10', NULL),
-- Amit A-1/501
(4, '2024-25', 120000.00, 'TDS-24-004', 'VERIFIED',  '2024-08-01', NULL),
-- Sunita T05-2501 (Case 5 scenario: submitted multiple times)
(5, '2024-25', 200000.00, 'TDS-24-005', 'SUBMITTED', '2024-09-01', 'Certificate submitted 3/4 times, amount needs update'),
(5, '2025-26', 75000.00,  'TDS-25-005', 'PENDING',   NULL,         'Pending submission'),
-- Vikram T03-1201
(6, '2024-25', 75000.00,  'TDS-24-006', 'VERIFIED',  '2024-10-01', NULL),
-- Neha GV-A/301
(7, '2024-25', 125000.00, 'TDS-24-007', 'SUBMITTED', '2025-01-15', NULL),
-- Kavita GV-B/102
(9, '2025-26', 200000.00, 'TDS-25-009', 'PENDING',   NULL,         NULL);

-- ── Cases (matching the 7 case types from the PDF) ──────────────────────────

INSERT INTO cases (case_ref, customer_id, booking_id, category, subject, description, status, priority, assigned_to, resolution) VALUES
-- Case 1: Payment update (Priya, R-109 plot - under 50L, no TDS)
('CASE-20260915-A1B2C3', 2, 3, 'PAYMENT_UPDATE',
 'Update balance payment for plot R-109',
 'Kindly update balance payment of plot num R-109. As TDS not required in R-109, this plot under 50 lakh. TDS not required to pay for this plot.',
 'OPEN', 'MEDIUM', 'Accounts Team', NULL),

-- Case 2: Sale deed delay (Rajesh, both flats)
('CASE-20260910-D4E5F6', 1, 1, 'SALE_DEED_DELAY',
 'Urgent: Sale Deed registration delay for B-2/202 and B-2/203',
 'HDFC Bank has issued a formal notice levying monthly delayed charges for non-submission of original property documents (registered Sale Deed) against the home loans. The failure to submit the original Sale Deed to the lending bank is strictly due to the ongoing delay on the part of Hero Realty in executing the registration process. Request: official explanation letter for the delay, and definitive timeline for Sale Deed execution.',
 'ESCALATED', 'URGENT', 'Legal Team', NULL),

-- Case 3: AFS document request (Rajesh, B-2/203)
('CASE-20260912-G7H8I9', 1, 2, 'DOCUMENT_REQUEST',
 'Request to dispatch AFS to communication address',
 'Please send my AFS to my communication address as I am not able to collect it from your office. Kindly pay attention to my humble request.',
 'OPEN', 'LOW', 'Documentation Team', NULL),

-- Case 4: Form 132 ledger update (Sunita, T05-2501)
('CASE-20260920-J1K2L3', 4, 5, 'PAYMENT_UPDATE',
 'Update ledger for Form 132 payment - July 2026',
 'PLEASE FIND ATTACHED FORMS 132 IN RESPECT OF PAYMENT MADE BY US IN JULY 2026. KINDLY UPDATE OUR LEDGER ACCORDINGLY.',
 'OPEN', 'MEDIUM', 'Accounts Team', NULL),

-- Case 5: TDS amount update (Sunita, T05-2501)
('CASE-20260918-M4N5O6', 4, 5, 'TDS_UPDATE',
 'TDS certificate submitted multiple times - update amount',
 'This is TDS amount whose certificate we have submitted more than 3/4 times. Kindly update TDS amount.',
 'IN_PROGRESS', 'HIGH', 'Accounts Team', NULL),

-- Case 6: Handover inquiry (Sunita, T05-2501)
('CASE-20260905-P7Q8R9', 4, 5, 'HANDOVER_INQUIRY',
 'Handover date confirmation for T05-2501',
 'Please refer trail email. The accounts team of Hero Homes has advised me to connect with you for handover process. Please confirm the earliest handover date of my flat T05-2501. Please confirm the process and also if anything required from my end in this regard for timely completion of the process.',
 'OPEN', 'HIGH', 'Handover Team', NULL),

-- Case 7: Registry schedule (Manoj, R-215)
('CASE-20260914-S1T2U3', 7, 8, 'REGISTRY_SCHEDULE',
 'Schedule registry on Monday 14/9/2026',
 'PLEASE MY REGISTRY SCHEDULE ON MONDAY 14/9/2026.',
 'OPEN', 'MEDIUM', 'Legal Team', NULL),

-- A resolved case for variety
('CASE-20260801-V4W5X6', 3, 4, 'DOCUMENT_REQUEST',
 'Request for allotment letter copy',
 'Please provide a copy of the allotment letter for flat A-1/501.',
 'RESOLVED', 'LOW', 'Documentation Team', 'Allotment letter copy dispatched via registered post on 2026-08-05.');

-- ── Case comments ───────────────────────────────────────────────────────────

INSERT INTO case_comments (case_id, author, comment) VALUES
(1, 'SYSTEM',       'Case raised: Update balance payment for plot R-109'),
(2, 'SYSTEM',       'Case raised: Urgent: Sale Deed registration delay for B-2/202 and B-2/203'),
(2, 'Legal Team',   'Escalated to senior management. HDFC notice copy received and forwarded.'),
(2, 'Rajesh Kumar', 'Any update on this? Bank is charging Rs 5000/month as penalty.'),
(3, 'SYSTEM',       'Case raised: Request to dispatch AFS to communication address'),
(4, 'SYSTEM',       'Case raised: Update ledger for Form 132 payment - July 2026'),
(5, 'SYSTEM',       'Case raised: TDS certificate submitted multiple times - update amount'),
(5, 'Accounts Team','Checking with records department. Previous submissions were not reflecting in system.'),
(6, 'SYSTEM',       'Case raised: Handover date confirmation for T05-2501'),
(7, 'SYSTEM',       'Case raised: Schedule registry on Monday 14/9/2026'),
(8, 'SYSTEM',       'Case raised: Request for allotment letter copy'),
(8, 'Documentation Team', 'Copy dispatched via registered post. Tracking ID: EE123456789IN');
