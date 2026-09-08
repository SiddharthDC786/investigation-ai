-- Synthetic crime network schema for PostgreSQL

CREATE TABLE IF NOT EXISTS cases (
    case_id VARCHAR(16) PRIMARY KEY,
    title VARCHAR(256) NOT NULL,
    description VARCHAR(512),
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS people (
    person_id VARCHAR(16) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    dob DATE NOT NULL,
    gender VARCHAR(16) NOT NULL,
    city VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS phones (
    phone_id VARCHAR(16) PRIMARY KEY,
    phone_number VARCHAR(16) NOT NULL UNIQUE,
    person_id VARCHAR(16) NOT NULL REFERENCES people(person_id)
);

CREATE TABLE IF NOT EXISTS bank_accounts (
    account_id VARCHAR(16) PRIMARY KEY,
    account_number VARCHAR(32) NOT NULL UNIQUE,
    person_id VARCHAR(16) NOT NULL REFERENCES people(person_id),
    bank_name VARCHAR(128) NOT NULL
);

CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id VARCHAR(16) PRIMARY KEY,
    registration_number VARCHAR(32) NOT NULL UNIQUE,
    person_id VARCHAR(16) NOT NULL REFERENCES people(person_id)
);

CREATE TABLE IF NOT EXISTS locations (
    location_id VARCHAR(16) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    city VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS organizations (
    org_id VARCHAR(16) PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    org_type VARCHAR(64) NOT NULL,
    city VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS cdr (
    cdr_id VARCHAR(16) PRIMARY KEY,
    caller_phone VARCHAR(16) NOT NULL,
    receiver_phone VARCHAR(16) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    duration_seconds INTEGER NOT NULL,
    tower_location VARCHAR(128) NOT NULL,
    case_id VARCHAR(16)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(16) PRIMARY KEY,
    sender_account VARCHAR(32) NOT NULL,
    receiver_account VARCHAR(32) NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    case_id VARCHAR(16)
);

CREATE TABLE IF NOT EXISTS fir (
    fir_id VARCHAR(16) PRIMARY KEY,
    case_id VARCHAR(16) NOT NULL,
    date DATE NOT NULL,
    police_station VARCHAR(128) NOT NULL,
    complaint_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fir_metadata (
    fir_id VARCHAR(16) PRIMARY KEY REFERENCES fir(fir_id),
    case_id VARCHAR(16) NOT NULL,
    report_type VARCHAR(32) NOT NULL
);

CREATE TABLE IF NOT EXISTS surveillance (
    surveillance_id VARCHAR(16) PRIMARY KEY,
    case_id VARCHAR(16) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    location VARCHAR(128) NOT NULL,
    report_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS case_references (
    reference_id VARCHAR(16) PRIMARY KEY,
    case_id VARCHAR(16) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    reference_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id VARCHAR(16) PRIMARY KEY,
    sender_phone VARCHAR(16) NOT NULL,
    receiver_phone VARCHAR(16) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    message_text TEXT NOT NULL,
    case_id VARCHAR(16)
);

CREATE TABLE IF NOT EXISTS relationships (
    relationship_id VARCHAR(16) PRIMARY KEY,
    person_id_a VARCHAR(16) NOT NULL REFERENCES people(person_id),
    person_id_b VARCHAR(16) NOT NULL REFERENCES people(person_id),
    relationship_type VARCHAR(64) NOT NULL,
    case_id VARCHAR(16) NOT NULL
);

CREATE TABLE IF NOT EXISTS ownership_history (
    ownership_id VARCHAR(16) PRIMARY KEY,
    asset_type VARCHAR(32) NOT NULL,
    asset_id VARCHAR(16) NOT NULL,
    person_id VARCHAR(16) NOT NULL REFERENCES people(person_id),
    valid_from DATE NOT NULL,
    valid_to DATE
);

CREATE TABLE IF NOT EXISTS private_events (
    event_id VARCHAR(16) PRIMARY KEY,
    person_id VARCHAR(16) NOT NULL REFERENCES people(person_id),
    event_type VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    description TEXT NOT NULL,
    case_id VARCHAR(16) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_private_events_case_id ON private_events(case_id);

-- Messy real-world identity records (typos, maiden/married names, manual entry errors)
CREATE TABLE IF NOT EXISTS recorded_names (
    record_id VARCHAR(16) PRIMARY KEY,
    case_id VARCHAR(16),
    source_type VARCHAR(64) NOT NULL,
    source_id VARCHAR(16) NOT NULL,
    recorded_name VARCHAR(128) NOT NULL,
    recorded_dob DATE,
    variant_type VARCHAR(64) NOT NULL,
    person_id VARCHAR(16) REFERENCES people(person_id),
    is_erroneous BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS recorded_phones (
    record_id VARCHAR(16) PRIMARY KEY,
    case_id VARCHAR(16),
    source_type VARCHAR(64) NOT NULL,
    source_id VARCHAR(16) NOT NULL,
    recorded_phone VARCHAR(20) NOT NULL,
    variant_type VARCHAR(64) NOT NULL,
    person_id VARCHAR(16) REFERENCES people(person_id),
    is_erroneous BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_recorded_names_person ON recorded_names(person_id);
CREATE INDEX IF NOT EXISTS idx_recorded_names_case ON recorded_names(case_id);
CREATE INDEX IF NOT EXISTS idx_recorded_phones_person ON recorded_phones(person_id);
CREATE INDEX IF NOT EXISTS idx_recorded_phones_phone ON recorded_phones(recorded_phone);
CREATE INDEX IF NOT EXISTS idx_cdr_case_id ON cdr(case_id);
CREATE INDEX IF NOT EXISTS idx_transactions_case_id ON transactions(case_id);
CREATE INDEX IF NOT EXISTS idx_fir_case_id ON fir(case_id);
CREATE INDEX IF NOT EXISTS idx_surveillance_case_id ON surveillance(case_id);
CREATE INDEX IF NOT EXISTS idx_chat_case_id ON chat_messages(case_id);
