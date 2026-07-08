"""
load_to_sqlite.py

Loads data/timesheet_raw.csv into data/timesheet.db as the `timesheets`
table, and creates a `valid_campuses` reference table used by the
referential integrity check in sql/validation_queries.sql.

Note on provenance: reconstructed script, see generate_data.py header
for context.
"""

import csv
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "timesheet_raw.csv"
DB_PATH = PROJECT_ROOT / "data" / "timesheet.db"

VALID_CAMPUSES = ["Campus A", "Campus B", "Campus C", "Campus D", "Campus E"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS timesheets (
    record_id       TEXT,
    employee_id     TEXT,
    employee_name   TEXT,
    campus          TEXT,
    department      TEXT,
    pay_period_end  TEXT,
    hours_worked    REAL,
    hourly_rate     REAL,
    calculated_pay  REAL,
    pay_status      TEXT,
    submitted_date  TEXT,
    approved_date   TEXT,
    supervisor_id   TEXT
);

CREATE TABLE IF NOT EXISTS valid_campuses (
    campus TEXT PRIMARY KEY
);
"""


def to_float_or_none(value):
    if value is None or value == "":
        return None
    return float(value)


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        rows = [
            (
                r["record_id"], r["employee_id"], r["employee_name"],
                r["campus"] or None, r["department"], r["pay_period_end"],
                to_float_or_none(r["hours_worked"]),
                to_float_or_none(r["hourly_rate"]),
                to_float_or_none(r["calculated_pay"]),
                r["pay_status"], r["submitted_date"], r["approved_date"],
                r["supervisor_id"],
            )
            for r in reader
        ]

    cur.executemany(
        """INSERT INTO timesheets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    cur.executemany(
        "INSERT INTO valid_campuses VALUES (?)",
        [(c,) for c in VALID_CAMPUSES],
    )

    conn.commit()

    n_timesheets = cur.execute("SELECT COUNT(*) FROM timesheets").fetchone()[0]
    n_campuses = cur.execute("SELECT COUNT(*) FROM valid_campuses").fetchone()[0]
    conn.close()

    print(f"Loaded {n_timesheets} rows into timesheets")
    print(f"Loaded {n_campuses} rows into valid_campuses")
    print(f"Database written to {DB_PATH}")


if __name__ == "__main__":
    main()
