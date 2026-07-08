"""
run_great_expectations.py

Builds a Great Expectations suite (Fluent API, GX 1.x) against the
timesheets table and writes:
  - reports/gx_findings_report.md
  - reports/gx_validation_results.json

Two checks in this project (pay reconciliation, approval sequencing) are
cross-column business rules with no single matching built-in expectation.
They're precomputed as derived boolean columns (pay_reconciles,
approval_sequence_valid) and validated with expect_column_values_to_be_in_set.

Expectations split into two tiers:
  - Hard blockers (default mostly=1.0): record_id null/uniqueness,
    hourly_rate null, pay reconciliation. Any failure here is a stop-ship
    data integrity problem, not a tolerance question.
  - Quality thresholds (mostly=0.95): value-range and categorical checks
    where a small defect rate is expected in real data and the suite is
    reporting rate, not demanding zero defects.

Note on provenance: reconstructed script, see generate_data.py header
for context.
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd
import great_expectations as gx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "timesheet.db"
MD_REPORT_PATH = PROJECT_ROOT / "reports" / "gx_findings_report.md"
JSON_REPORT_PATH = PROJECT_ROOT / "reports" / "gx_validation_results.json"

VALID_CAMPUSES = ["Campus A", "Campus B", "Campus C", "Campus D", "Campus E"]
VALID_STATUSES = ["Approved", "Pending", "Rejected", "Processing"]
MIN_WAGE = 7.25


def load_dataframe():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM timesheets", conn)
    conn.close()

    df["pay_reconciles"] = df["hourly_rate"].notna() & (
        (df["calculated_pay"] - (df["hours_worked"] * df["hourly_rate"])).abs() <= 0.02
    )
    df["approval_sequence_valid"] = pd.to_datetime(df["approved_date"]) >= pd.to_datetime(
        df["submitted_date"]
    )
    return df


def build_expectations():
    e = gx.expectations
    return [
        e.ExpectColumnValuesToNotBeNull(column="record_id"),
        e.ExpectColumnValuesToBeUnique(column="record_id"),
        e.ExpectColumnValuesToNotBeNull(column="hourly_rate"),
        e.ExpectColumnValuesToBeBetween(
            column="hourly_rate", min_value=MIN_WAGE, strict_min=False, mostly=0.95
        ),
        e.ExpectColumnValuesToNotBeNull(column="campus", mostly=0.95),
        e.ExpectColumnValuesToBeInSet(column="campus", value_set=VALID_CAMPUSES, mostly=0.95),
        e.ExpectColumnValuesToBeBetween(
            column="hours_worked", min_value=0, strict_min=True, max_value=40, mostly=0.95
        ),
        e.ExpectColumnValuesToBeInSet(column="pay_status", value_set=VALID_STATUSES, mostly=0.95),
        e.ExpectColumnValuesToBeInSet(column="pay_reconciles", value_set=[True]),
        e.ExpectColumnValuesToBeInSet(
            column="approval_sequence_valid", value_set=[True], mostly=0.95
        ),
    ]


def main():
    df = load_dataframe()

    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas("timesheet_source")
    data_asset = data_source.add_dataframe_asset(name="timesheets")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("timesheets_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    n_rows = len(df)
    results = []
    for expectation in build_expectations():
        result = batch.validate(expectation)
        res_dict = result.to_json_dict()
        results.append(res_dict)

    overall_success = all(r["success"] for r in results)

    # --- markdown report ---
    md_lines = [
        "# Great Expectations Validation Report",
        "",
        f"**Overall success:** {overall_success}",
        "",
        "| Expectation | Column | Success | Unexpected Count | Unexpected % |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        cfg = r["expectation_config"]
        exp_type = cfg["type"]
        column = cfg["kwargs"].get("column", "")
        success = r["success"]
        unexpected_count = r["result"].get("unexpected_count", 0)
        unexpected_pct = r["result"].get("unexpected_percent", 0.0) or 0.0
        md_lines.append(
            f"| {exp_type} | {column} | {success} | {unexpected_count} | {unexpected_pct:.2f}% |"
        )
    MD_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT_PATH.write_text("\n".join(md_lines) + "\n")

    # --- json report ---
    json_report = {
        "success": overall_success,
        "row_count": n_rows,
        "results": results,
    }
    JSON_REPORT_PATH.write_text(json.dumps(json_report, indent=2, default=str))

    print(f"Wrote {MD_REPORT_PATH}")
    print(f"Wrote {JSON_REPORT_PATH}")
    print(f"Overall success: {overall_success}")
    for r in results:
        cfg = r["expectation_config"]
        print(
            f"  {cfg['type']} ({cfg['kwargs'].get('column','')}): "
            f"success={r['success']} unexpected={r['result'].get('unexpected_count', 0)}"
        )


if __name__ == "__main__":
    main()
