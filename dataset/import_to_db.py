#!/usr/bin/env python3
"""Load generated CSV files into the crime_network PostgreSQL database."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

PSQL = "/Applications/Postgres.app/Contents/Versions/latest/bin/psql"

TABLES = [
    ("people.csv", "people", "(person_id, name, dob, gender, city)"),
    ("phones.csv", "phones", "(phone_id, phone_number, person_id)"),
    ("bank_accounts.csv", "bank_accounts", "(account_id, account_number, person_id, bank_name)"),
    ("vehicles.csv", "vehicles", "(vehicle_id, registration_number, person_id)"),
    ("locations.csv", "locations", "(location_id, name, city)"),
    ("organizations.csv", "organizations", "(org_id, name, org_type, city)"),
    ("cases.csv", "cases", "(case_id, title, description, status, created_at)"),
    ("fir.csv", "fir", "(fir_id, case_id, date, police_station, complaint_text)"),
    ("fir_metadata.csv", "fir_metadata", "(fir_id, case_id, report_type)"),
    ("surveillance.csv", "surveillance", "(surveillance_id, case_id, timestamp, location, report_text)"),
    ("case_references.csv", "case_references", "(reference_id, case_id, source_type, reference_text)"),
    ("relationships.csv", "relationships", "(relationship_id, person_id_a, person_id_b, relationship_type, case_id)"),
    (
        "recorded_names.csv",
        "recorded_names",
        "(record_id, case_id, source_type, source_id, recorded_name, recorded_dob, variant_type, person_id, is_erroneous)",
    ),
    (
        "recorded_phones.csv",
        "recorded_phones",
        "(record_id, case_id, source_type, source_id, recorded_phone, variant_type, person_id, is_erroneous)",
    ),
    ("ownership_history.csv", "ownership_history", "(ownership_id, asset_type, asset_id, person_id, valid_from, valid_to)"),
    (
        "private_events.csv",
        "private_events",
        "(event_id, person_id, event_type, timestamp, description, case_id)",
    ),
    ("cdr.csv", "cdr", "(cdr_id, caller_phone, receiver_phone, timestamp, duration_seconds, tower_location, case_id)"),
    (
        "transactions.csv",
        "transactions",
        "(transaction_id, sender_account, receiver_account, amount, timestamp, case_id)",
    ),
    (
        "chat_messages.csv",
        "chat_messages",
        "(message_id, sender_phone, receiver_phone, timestamp, message_text, case_id)",
    ),
]


def run_psql(database: str, host: str, port: int, user: str, password: str, sql: str) -> None:
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    subprocess.run(
        [PSQL, "-h", host, "-p", str(port), "-U", user, "-d", database, "-v", "ON_ERROR_STOP=1", "-c", sql],
        check=True,
        env=env,
    )


def run_psql_file(database: str, host: str, port: int, user: str, password: str, file_path: Path) -> None:
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    subprocess.run(
        [PSQL, "-h", host, "-p", str(port), "-U", user, "-d", database, "-v", "ON_ERROR_STOP=1", "-f", str(file_path)],
        check=True,
        env=env,
    )


def import_csv(database: str, host: str, port: int, user: str, password: str, data_dir: Path, csv_name: str, table: str, columns: str) -> None:
    csv_path = data_dir / csv_name
    sql = (
        f"\\copy {table}{columns} FROM '{csv_path.resolve()}' "
        "WITH (FORMAT csv, HEADER true, NULL '')"
    )
    run_psql(database, host, port, user, password, sql)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import synthetic dataset CSV files into PostgreSQL.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--database", default="crime_network")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="2007")
    parser.add_argument("--schema-file", type=Path, default=Path("schema.sql"))
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables before import.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.reset:
        drop_sql = "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
        run_psql(args.database, args.host, args.port, args.user, args.password, drop_sql)

    run_psql_file(args.database, args.host, args.port, args.user, args.password, args.schema_file)

    for csv_name, table, columns in TABLES:
        print(f"Importing {csv_name} -> {table}...")
        import_csv(args.database, args.host, args.port, args.user, args.password, args.data_dir, csv_name, table, columns)

    counts_sql = """
    SELECT 'people' AS table_name, COUNT(*) AS row_count FROM people
    UNION ALL SELECT 'phones', COUNT(*) FROM phones
    UNION ALL SELECT 'bank_accounts', COUNT(*) FROM bank_accounts
    UNION ALL SELECT 'vehicles', COUNT(*) FROM vehicles
    UNION ALL SELECT 'locations', COUNT(*) FROM locations
    UNION ALL SELECT 'organizations', COUNT(*) FROM organizations
    UNION ALL SELECT 'cases', COUNT(*) FROM cases
    UNION ALL SELECT 'cdr', COUNT(*) FROM cdr
    UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
    UNION ALL SELECT 'fir', COUNT(*) FROM fir
    UNION ALL SELECT 'surveillance', COUNT(*) FROM surveillance
    UNION ALL SELECT 'case_references', COUNT(*) FROM case_references
    UNION ALL SELECT 'chat_messages', COUNT(*) FROM chat_messages
    UNION ALL SELECT 'private_events', COUNT(*) FROM private_events
    UNION ALL SELECT 'recorded_names', COUNT(*) FROM recorded_names
    UNION ALL SELECT 'recorded_phones', COUNT(*) FROM recorded_phones
    ORDER BY table_name;
    """
    run_psql(args.database, args.host, args.port, args.user, args.password, counts_sql)
    print("Import complete.")


if __name__ == "__main__":
    main()
