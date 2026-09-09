-- Demo seed: multiple "Rahul" identities in CASE0001 with distinct roles and evidence weights.
-- Safe to re-run (uses ON CONFLICT / NOT EXISTS patterns).

-- Ensure phones for key Rahuls (skip numbers already registered)
INSERT INTO phones (phone_id, phone_number, person_id)
SELECT v.phone_id, v.phone_number, v.person_id
FROM (VALUES
  ('PH-D003', '8871205599', 'P01301'),
  ('PH-D004', '6749921651', 'P01301'),
  ('PH-D005', '6851846689', 'P01225'),
  ('PH-D006', '9123456780', 'P00971'),
  ('PH-D007', '9988776655', 'P01189'),
  ('PH-D008', '7766554433', 'P00136'),
  ('PH-D009', '6655443322', 'P00088'),
  ('PH-D010', '5544332211', 'P00735')
) AS v(phone_id, phone_number, person_id)
WHERE NOT EXISTS (
  SELECT 1 FROM phones p WHERE p.phone_number = v.phone_number OR p.phone_id = v.phone_id
);

-- CASE0001 relationship graph (roles inferred at runtime)
INSERT INTO relationships (relationship_id, person_id_a, person_id_b, relationship_type, case_id) VALUES
  ('REL-D001', 'P00014', 'P00971', 'handler', 'CASE0001'),
  ('REL-D002', 'P00014', 'P01189', 'associate', 'CASE0001'),
  ('REL-D003', 'P00014', 'P01301', 'associate', 'CASE0001'),
  ('REL-D004', 'P00014', 'P01225', 'associate', 'CASE0001'),
  ('REL-D005', 'P00014', 'P00136', 'facilitator', 'CASE0001'),
  ('REL-D006', 'P00014', 'P00436', 'business_partner', 'CASE0001'),
  ('REL-D007', 'P00014', 'P00088', 'tenant', 'CASE0001'),
  ('REL-D008', 'P00014', 'P00735', 'tenant', 'CASE0001'),
  ('REL-D009', 'P01301', 'P01225', 'associate', 'CASE0001'),
  ('REL-D010', 'P00971', 'P00136', 'facilitator', 'CASE0001')
ON CONFLICT (relationship_id) DO NOTHING;

-- CDR evidence: P00014 primary suspect, P01301/P01225 secondary suspects, low for witnesses
INSERT INTO cdr (cdr_id, caller_phone, receiver_phone, timestamp, duration_seconds, tower_location, case_id)
SELECT
  'CDR-D' || LPAD(g.i::text, 4, '0'),
  CASE WHEN g.i % 2 = 0 THEN '6245531290' ELSE '9783471062' END,
  CASE WHEN g.i % 3 = 0 THEN '8871205599' WHEN g.i % 3 = 1 THEN '6851846689' ELSE '9123456780' END,
  (TIMESTAMP '2025-06-01 08:00:00' + (g.i || ' hours')::interval),
  60 + (g.i % 120),
  CASE WHEN g.i % 2 = 0 THEN 'Hyderabad Tower 12' ELSE 'Mumbai Tower 4' END,
  'CASE0001'
FROM generate_series(1, 45) AS g(i)
WHERE NOT EXISTS (SELECT 1 FROM cdr WHERE cdr_id = 'CDR-D' || LPAD(g.i::text, 4, '0'));

INSERT INTO cdr (cdr_id, caller_phone, receiver_phone, timestamp, duration_seconds, tower_location, case_id)
SELECT
  'CDR-D1' || LPAD(g.i::text, 4, '0'),
  '8871205599',
  '6749921640',
  (TIMESTAMP '2025-07-01 10:00:00' + (g.i || ' hours')::interval),
  45 + g.i,
  'Mumbai Lokhandwala',
  'CASE0001'
FROM generate_series(1, 22) AS g(i)
WHERE NOT EXISTS (SELECT 1 FROM cdr WHERE cdr_id = 'CDR-D1' || LPAD(g.i::text, 4, '0'));

INSERT INTO cdr (cdr_id, caller_phone, receiver_phone, timestamp, duration_seconds, tower_location, case_id)
SELECT
  'CDR-D2' || LPAD(g.i::text, 4, '0'),
  '6851846689',
  '9988776655',
  (TIMESTAMP '2025-07-15 14:00:00' + (g.i || ' hours')::interval),
  30 + g.i,
  'Bhopal Central',
  'CASE0001'
FROM generate_series(1, 14) AS g(i)
WHERE NOT EXISTS (SELECT 1 FROM cdr WHERE cdr_id = 'CDR-D2' || LPAD(g.i::text, 4, '0'));

INSERT INTO cdr (cdr_id, caller_phone, receiver_phone, timestamp, duration_seconds, tower_location, case_id)
SELECT
  'CDR-DW' || LPAD(g.i::text, 4, '0'),
  '6655443322',
  '5544332211',
  (TIMESTAMP '2025-08-01 09:00:00' + (g.i || ' hours')::interval),
  15,
  'Nagpur witness tower',
  'CASE0001'
FROM generate_series(1, 2) AS g(i)
WHERE NOT EXISTS (SELECT 1 FROM cdr WHERE cdr_id = 'CDR-DW' || LPAD(g.i::text, 4, '0'));

-- FIR mentions for evidence scoring (full names where possible)
UPDATE fir SET complaint_text = complaint_text || E'\n\nDemo network: suspect Rahul Mukherjee (Hyderabad) coordinated with handler Rahul Verma (Mumbai), associate Rahul Nair (Hyderabad), facilitator Rahul Ali (Mumbai), and witnesses Rahul Patel (Nagpur) and Rahul Singh (Kolkata). Secondary suspect Rahul Mukherjee (Mumbai/Bhopal) also named.'
WHERE case_id = 'CASE0001' AND fir_id = (SELECT fir_id FROM fir WHERE case_id = 'CASE0001' ORDER BY date LIMIT 1)
  AND complaint_text NOT LIKE '%Demo network:%';
