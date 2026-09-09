#!/usr/bin/env python3
"""Apply demo Rahul network seed to the running PostgreSQL database."""

from __future__ import annotations

import os
from pathlib import Path

try:
    import psycopg
except ImportError:
    raise SystemExit("Install psycopg: pip install psycopg[binary]")

SQL_FILE = Path(__file__).resolve().parent / "seed_demo_rahuls.sql"


def main() -> None:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql://vigil:vigil2026@localhost:5432/crime_network",
    )
    sql = SQL_FILE.read_text(encoding="utf-8")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print(f"Applied demo Rahul seed from {SQL_FILE.name}")


if __name__ == "__main__":
    main()
