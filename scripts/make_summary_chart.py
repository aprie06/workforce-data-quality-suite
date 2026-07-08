"""
make_summary_chart.py

Generates reports/defect_summary_chart.png: a ranked horizontal bar chart
of rows flagged by each SQL validation check, read directly from
data/timesheet.db so the chart always reflects the actual current data,
not a static/hardcoded figure.
"""

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "timesheet.db"
CHART_PATH = PROJECT_ROOT / "reports" / "defect_summary_chart.png"

PALETTE = "#4C72B0"

CHECKS = {
    "Pay reconciliation mismatch": """
        SELECT COUNT(*) FROM timesheets
        WHERE hourly_rate IS NOT NULL
          AND ABS(calculated_pay - (hours_worked * hourly_rate)) > 0.02
    """,
    "Missing required fields": """
        SELECT COUNT(*) FROM timesheets
        WHERE hourly_rate IS NULL OR campus IS NULL OR TRIM(campus) = ''
    """,
    "Hours worked out of range": """
        SELECT COUNT(*) FROM timesheets WHERE hours_worked <= 0 OR hours_worked > 40
    """,
    "Rate below minimum wage": """
        SELECT COUNT(*) FROM timesheets WHERE hourly_rate IS NOT NULL AND hourly_rate < 7.25
    """,
    "Approval before submission": """
        SELECT COUNT(*) FROM timesheets WHERE approved_date < submitted_date
    """,
    "Invalid campus code": """
        SELECT COUNT(*) FROM timesheets t
        LEFT JOIN valid_campuses v ON t.campus = v.campus
        WHERE t.campus IS NOT NULL AND v.campus IS NULL
    """,
    "Duplicate record_id": """
        SELECT COUNT(*) FROM (
            SELECT record_id FROM timesheets GROUP BY record_id HAVING COUNT(*) > 1
        )
    """,
    "Invalid pay_status": """
        SELECT COUNT(*) FROM timesheets
        WHERE pay_status NOT IN ('Approved','Pending','Rejected','Processing')
    """,
}


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    counts = {}
    for label, sql in CHECKS.items():
        cur.execute(sql)
        counts[label] = cur.fetchone()[0]
    conn.close()

    items = sorted(counts.items(), key=lambda kv: kv[1])
    labels = [k for k, _ in items]
    values = [v for _, v in items]

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update({
        "figure.dpi": 150,
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
    })

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.barh(labels, values, color=PALETTE)

    for bar in bars:
        width = bar.get_width()
        ax.text(width + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{int(width)}", ha="left", va="center", fontsize=10)

    ax.set_title("Rows Flagged by Validation Check", fontweight="bold")
    ax.set_xlabel("Rows flagged (of 2,512 total)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(0, max(values) * 1.15)

    plt.tight_layout()
    CHART_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(CHART_PATH, dpi=150, bbox_inches="tight")
    print(f"Wrote chart to {CHART_PATH}")


if __name__ == "__main__":
    main()
