"""
generate_data.py

Builds the synthetic timesheet dataset used by this project.

Note on provenance: this script was reconstructed after the original was
lost. It is written to reproduce the same dataset design documented in
README.md and reports/sql_findings_report.md: same columns, same valid
value sets, same defect categories injected at the same counts. It is not
a byte-for-byte recovery of the original generator, since the original
random seed and exact implementation were not recoverable. Running this
script reproduces the documented defect counts exactly, by construction,
because each defect category is injected at a fixed target count rather
than a probabilistic rate.

Output: data/timesheet_raw.csv
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
random.seed(SEED)

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "timesheet_raw.csv"

N_BASE_RECORDS = 2500
N_EMPLOYEES = 767
N_SUPERVISORS = 40

VALID_CAMPUSES = ["Campus A", "Campus B", "Campus C", "Campus D", "Campus E"]
INVALID_CAMPUS = "Campus Z"

DEPARTMENTS = [
    "Admissions", "Career Services", "Facilities", "Financial Aid",
    "IT Services", "Library", "Registrar", "Student Success",
]

VALID_STATUSES = ["Approved", "Pending", "Rejected", "Processing"]
INVALID_STATUS = "Unknown"

PERIOD_START = date(2026, 1, 1)
PERIOD_END = date(2026, 6, 30)

MIN_WAGE = 7.25

# Target defect counts, matched to reports/sql_findings_report.md
N_DUPLICATE = 12
N_MISSING_RATE = 38
N_MISSING_CAMPUS = 15
N_HOURS_NEGATIVE = 17
N_HOURS_EXCESSIVE = 17
N_BELOW_MIN_WAGE = 25
N_PAY_MISMATCH = 106
N_APPROVAL_SEQUENCE_BROKEN = 18
N_INVALID_CAMPUS = 10
N_INVALID_STATUS = 8


def random_date(start: date, end: date) -> date:
    span = (end - start).days
    return start + timedelta(days=random.randint(0, span))


def build_employee_pool():
    employee_ids = random.sample(range(1000, 1000 + max(N_EMPLOYEES, 800)), N_EMPLOYEES)
    return [f"EMP-{eid}" for eid in employee_ids]


def build_supervisor_pool():
    return [f"SUP-{i:03d}" for i in range(1, N_SUPERVISORS + 1)]


def main():
    employee_pool = build_employee_pool()
    supervisor_pool = build_supervisor_pool()

    rows = []
    for i in range(1, N_BASE_RECORDS + 1):
        record_id = f"TS-{i:06d}"
        employee_id = random.choice(employee_pool)
        employee_name = f"Employee {random.randint(1000, 1999)}"
        campus = random.choice(VALID_CAMPUSES)
        department = random.choice(DEPARTMENTS)

        pay_period_end = random_date(PERIOD_START, PERIOD_END)
        submitted_date = pay_period_end + timedelta(days=random.randint(0, 3))
        approved_date = submitted_date + timedelta(days=random.randint(1, 5))

        hours_worked = round(random.uniform(1.0, 40.0), 2)
        hourly_rate = round(random.uniform(MIN_WAGE, 30.0), 2)
        calculated_pay = round(hours_worked * hourly_rate, 2)

        pay_status = random.choice(VALID_STATUSES)
        supervisor_id = random.choice(supervisor_pool)

        rows.append({
            "record_id": record_id,
            "employee_id": employee_id,
            "employee_name": employee_name,
            "campus": campus,
            "department": department,
            "pay_period_end": pay_period_end.isoformat(),
            "hours_worked": hours_worked,
            "hourly_rate": hourly_rate,
            "calculated_pay": calculated_pay,
            "pay_status": pay_status,
            "submitted_date": submitted_date.isoformat(),
            "approved_date": approved_date.isoformat(),
            "supervisor_id": supervisor_id,
        })

    # Build disjoint index pools for each defect category so counts land
    # exactly on the documented targets with no cross-category collisions.
    all_indices = list(range(N_BASE_RECORDS))
    random.shuffle(all_indices)

    pools = {}
    cursor = 0
    for name, n in [
        ("missing_rate", N_MISSING_RATE),
        ("missing_campus", N_MISSING_CAMPUS),
        ("hours_negative", N_HOURS_NEGATIVE),
        ("hours_excessive", N_HOURS_EXCESSIVE),
        ("below_min_wage", N_BELOW_MIN_WAGE),
        ("pay_mismatch", N_PAY_MISMATCH),
        ("approval_broken", N_APPROVAL_SEQUENCE_BROKEN),
        ("invalid_campus", N_INVALID_CAMPUS),
        ("invalid_status", N_INVALID_STATUS),
    ]:
        pools[name] = all_indices[cursor:cursor + n]
        cursor += n

    for idx in pools["missing_rate"]:
        rows[idx]["hourly_rate"] = ""
        rows[idx]["calculated_pay"] = ""

    for idx in pools["missing_campus"]:
        rows[idx]["campus"] = ""

    for idx in pools["hours_negative"]:
        rows[idx]["hours_worked"] = round(random.uniform(-10.0, -0.5), 2)
        if rows[idx]["hourly_rate"] != "":
            rows[idx]["calculated_pay"] = round(
                rows[idx]["hours_worked"] * rows[idx]["hourly_rate"], 2
            )

    for idx in pools["hours_excessive"]:
        rows[idx]["hours_worked"] = round(random.uniform(41.0, 115.0), 2)
        if rows[idx]["hourly_rate"] != "":
            rows[idx]["calculated_pay"] = round(
                rows[idx]["hours_worked"] * rows[idx]["hourly_rate"], 2
            )

    for idx in pools["below_min_wage"]:
        rows[idx]["hourly_rate"] = round(random.uniform(4.25, 7.24), 2)
        rows[idx]["calculated_pay"] = round(
            rows[idx]["hours_worked"] * rows[idx]["hourly_rate"], 2
        )

    for idx in pools["pay_mismatch"]:
        if rows[idx]["hourly_rate"] == "":
            continue
        true_pay = rows[idx]["hours_worked"] * rows[idx]["hourly_rate"]
        # Mimics a stale/short-calculated pay bug: reported pay is well
        # below what hours x rate actually produces.
        rows[idx]["calculated_pay"] = round(true_pay * random.uniform(0.05, 0.5), 2)

    for idx in pools["approval_broken"]:
        submitted = date.fromisoformat(rows[idx]["submitted_date"])
        rows[idx]["approved_date"] = (
            submitted - timedelta(days=random.randint(1, 9))
        ).isoformat()

    for idx in pools["invalid_campus"]:
        rows[idx]["campus"] = INVALID_CAMPUS

    for idx in pools["invalid_status"]:
        rows[idx]["pay_status"] = INVALID_STATUS

    # Duplicate N_DUPLICATE existing rows to create repeated record_ids.
    dup_source_indices = random.sample(range(N_BASE_RECORDS), N_DUPLICATE)
    duplicated_rows = [dict(rows[i]) for i in dup_source_indices]
    rows.extend(duplicated_rows)

    random.shuffle(rows)

    fieldnames = [
        "record_id", "employee_id", "employee_name", "campus", "department",
        "pay_period_end", "hours_worked", "hourly_rate", "calculated_pay",
        "pay_status", "submitted_date", "approved_date", "supervisor_id",
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")
    print(f"  base records: {N_BASE_RECORDS}, duplicated: {N_DUPLICATE}")


if __name__ == "__main__":
    main()
