-- Minimal CI/test seed for CASE0001 (safe to re-run)

INSERT INTO cases (case_id, title, description, status)
VALUES ('CASE0001', 'CI Demo Case', 'Seeded for pytest and eval', 'OPEN')
ON CONFLICT (case_id) DO NOTHING;

INSERT INTO people (person_id, name, dob, gender, city) VALUES
  ('P00014', 'Rahul Mukherjee', '1990-04-12', 'Male', 'Hyderabad'),
  ('P01301', 'Rahul Sharma', '1985-08-03', 'Male', 'Mumbai'),
  ('P01225', 'Rahul Sharma', '1992-11-19', 'Male', 'Chennai'),
  ('P00062', 'Rahul Patel', '1988-02-01', 'Male', 'Nagpur')
ON CONFLICT (person_id) DO NOTHING;

INSERT INTO phones (phone_id, phone_number, person_id) VALUES
  ('PH-CI01', '9783471062', 'P00014'),
  ('PH-CI02', '8871205599', 'P01301'),
  ('PH-CI03', '6851846689', 'P01225')
ON CONFLICT (phone_id) DO NOTHING;

INSERT INTO relationships (relationship_id, person_id_a, person_id_b, relationship_type, case_id) VALUES
  ('REL-CI01', 'P00014', 'P01301', 'associate', 'CASE0001'),
  ('REL-CI02', 'P00014', 'P01225', 'associate', 'CASE0001')
ON CONFLICT (relationship_id) DO NOTHING;

INSERT INTO fir (fir_id, case_id, date, police_station, complaint_text) VALUES
  ('FIR-CI01', 'CASE0001', CURRENT_DATE, 'Cyber Cell', 'Suspect Rahul Mukherjee (Hyderabad) contacted associate Rahul Sharma (Mumbai).')
ON CONFLICT (fir_id) DO UPDATE SET complaint_text = EXCLUDED.complaint_text;

INSERT INTO cdr (cdr_id, caller_phone, receiver_phone, timestamp, duration_seconds, tower_location, case_id) VALUES
  ('CDR-CI01', '9783471062', '8871205599', NOW(), 120, 'Hyderabad', 'CASE0001')
ON CONFLICT (cdr_id) DO NOTHING;
