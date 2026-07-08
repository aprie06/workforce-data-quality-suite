"""
run_sql_checks.py

Runs each named validation query in sql/validation_queries.sql against
data/timesheet.db and writes reports/sql_findings_report.md.

Note on provenance: reconstructed script, see generate_data.py header
for context.
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "timesheet.db"
REPORT_PATH = PROJECT_ROOT / "reports" / "sql_findings_report.md"

CHECKS = [
    (
        "Duplicate record_id",
        """
        SELECT record_id, COUNT(*) AS occurrence_count
        FROM timesheets
        GROUP BY record_id
        HAVING COUNT(*) > 1
        ORDER BY occurrence_count DESC;
        """,
        "duplicate_record_id",
    ),
    (
        "Missing required fields (hourly_rate, campus)",
        """
        SELECT record_id, employee_id, campus, hourly_rate
        FROM timesheets
        WHERE hourly_rate IS NULL OR campus IS NULL OR TRIM(campus) = '';
        """,
        "missing_required_field",
    ),
    (
        "Hours worked outside a valid range",
        """
        SELECT record_id, employee_id, hours_worked,
            CASE
                WHEN hours_worked <= 0 THEN 'negative_or_zero'
                WHEN hours_worked > 40 THEN 'exceeds_realistic_cap'
            END AS issue_type
        FROM timesheets
        WHERE hours_worked <= 0 OR hours_worked > 40;
        """,
        "hours_worked_out_of_range",
    ),
    (
        "Hourly rate below minimum wage",
        """
        SELECT record_id, employee_id, hourly_rate
        FROM timesheets
        WHERE hourly_rate IS NOT NULL AND hourly_rate < 7.25;
        """,
        "hourly_rate_below_minimum_wage",
    ),
    (
        "Pay reconciliation mismatch",
        """
        SELECT record_id, employee_id, hours_worked, hourly_rate,
            calculated_pay,
            ROUND(hours_worked * hourly_rate, 2) AS expected_pay,
            ROUND(calculated_pay - (hours_worked * hourly_rate), 2) AS variance
        FROM timesheets
        WHERE hourly_rate IS NOT NULL
          AND ABS(calculated_pay - (hours_worked * hourly_rate)) > 0.02
        ORDER BY ABS(calculated_pay - (hours_worked * hourly_rate)) DESC;
        """,
        "pay_reconciliation_mismatch",
    ),
    (
        "Approval sequencing errors (approved before submitted)",
        """
        SELECT record_id, employee_id, submitted_date, approved_date,
            CAST(julianday(approved_date) - julianday(submitted_date) AS INTEGER) AS days_variance
        FROM timesheets
        WHERE approved_date < submitted_date;
        """,
        "approved_before_submitted",
    ),
    (
        "Invalid campus code (referential integrity)",
        """
        SELECT t.record_id, t.employee_id, t.campus
        FROM timesheets t
        LEFT JOIN valid_campuses v ON t.campus = v.campus
        WHERE t.campus IS NOT NULL AND v.campus IS NULL;
        """,
        "invalid_campus_code",
    ),
    (
        "Invalid pay_status values",
        """
        SELECT record_id, employee_id, pay_status
        FROM timesheets
        WHERE pay_status NOT IN ('Approved', 'Pending', 'Rejected', 'Processing');
        """,
        "invalid_pay_status",
    ),
]


def rows_to_markdown_table(columns, rows):
    header = "| " + " | ".join(columns) + " |"
    sep = "|" + "|".join(":---" if i == 0 else "---:" for i in range(len(columns))) + "|"
    lines = [header, sep]
    for row in rows:
        cells = []
        for v in row:
            cells.append("nan" if v is None else str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sections = []
    summary_rows = []

    for i, (title, sql, key) in enumerate(CHECKS, start=1):
        cur.execute(sql)
        result_rows = cur.fetchall()
        columns = [d[0] for d in cur.description]
        n = len(result_rows)
        summary_rows.append((title, n))

        section = [f"## {i}. {title}", "", f"**Rows returned:** {n}", ""]
        if n > 5:
            section.append(f"(showing first 5 of {n} rows)")
            section.append("")
        preview = [tuple(r) for r in result_rows[:5]]
        if preview:
            section.append(rows_to_markdown_table(columns, preview))
        sections.append("\n".join(section))

    conn.close()

    summary_header = "| Check | Rows Flagged |\n|:---|---:|"
    summary_lines = [summary_header]
    for i, (title, n) in enumerate(summary_rows, start=1):
        summary_lines.append(f"| {i}. {title} | {n} |")
    summary_section = "## Summary\n\n" + "\n".join(summary_lines)

    report = (
        "# SQL Data Quality Findings Report\n\n"
        "Each section below corresponds to a named check in "
        "`sql/validation_queries.sql`. Row counts reflect what the query "
        "found against the current dataset.\n\n"
        + "\n\n".join(sections)
        + "\n\n"
        + summary_section
        + "\n"
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report)
    print(f"Wrote findings report to {REPORT_PATH}")
    for title, n in summary_rows:
        print(f"  {title}: {n}")


if __name__ == "__main__":
    main()
