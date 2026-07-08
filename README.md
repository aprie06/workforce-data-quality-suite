# Timesheet & Workforce Data Quality Suite

A data quality validation pipeline for multi-site workforce timesheet data,
combining SQL-based business rule checks with an automated Great
Expectations suite. Built to demonstrate the same validation logic used to
catch timesheet and hours-to-pay errors before they reach an approval cycle,
applied to a synthetic dataset modeled on multi-campus, multi-department
timesheet submissions.

## Why This Matters Now

Timesheet data breaks in predictable, recurring ways across any multi-site
workforce program: a rate entered below minimum wage, a duplicate
submission from a batch upload, an approval logged before the submission
it's approving, hours that don't reconcile with the calculated pay amount.
In a manual review process, these errors are caught by someone noticing
something looks off across dozens or hundreds of records, if they're caught
at all before the cycle closes. This project builds the automated layer
that catches them first, every time, without depending on a person
happening to review the right row.

This mirrors real timesheet supervision work: validating batch submissions
across multiple sites and departments, catching reconciliation errors
before they reach an approval cycle, and treating data integrity as a
process to build and automate, not a task to repeat manually every cycle.

## What This Project Demonstrates

- **SQL**: eight named validation queries covering referential integrity,
  business rule violations, and hours-to-pay reconciliation, plus a summary
  rollup query suitable for a stakeholder-facing dashboard.
- **Automated testing with Great Expectations**: a repeatable expectation
  suite that runs the same checks programmatically, returns a structured
  pass/fail result, and is built to slot into a scheduled pipeline rather
  than be run by hand.
- **Realistic, intentional data quality issues**: the dataset isn't clean
  data with the checks built to match it. Defects were injected first, at
  known rates, then the validation layer was built independently to find
  them, which is closer to how real data quality work actually happens.

## Project Structure

```
workforce-data-quality-suite/
├── data/
│   ├── timesheet_raw.csv        # synthetic dataset with injected defects
│   └── timesheet.db             # SQLite database used by the SQL layer
├── sql/
│   └── validation_queries.sql   # documented, standalone SQL checks
├── scripts/
│   ├── generate_data.py         # builds the synthetic dataset
│   ├── load_to_sqlite.py        # loads CSV into SQLite
│   ├── run_sql_checks.py        # runs SQL checks, writes findings report
│   └── run_great_expectations.py# builds and runs the GX suite
└── reports/
    ├── sql_findings_report.md
    ├── gx_findings_report.md
    └── gx_validation_results.json
```

## How to Run

```bash
pip install -r requirements.txt

python scripts/generate_data.py          # generate synthetic dataset
python scripts/load_to_sqlite.py         # load into SQLite
python scripts/run_sql_checks.py         # run SQL validation, write report
python scripts/run_great_expectations.py # run GX suite, write report
```

## Data Quality Checks Implemented

| Check | Type | What it catches |
|---|---|---|
| Duplicate record_id | SQL + GX | Re-submitted or double-loaded timesheet records |
| Missing hourly_rate / site | SQL + GX | Incomplete records that can't clear approval as-is |
| Hours worked out of range | SQL + GX | Negative, zero, or implausibly high hours |
| Hourly rate below minimum wage | SQL + GX | Compliance violations or entry errors |
| Hours-to-pay reconciliation | SQL + GX | Calculated pay that doesn't match hours × rate |
| Approval before submission | SQL + GX | Broken or backdated approval workflow |
| Invalid site code | SQL + GX | Referential integrity against a valid site list |
| Invalid status value | SQL + GX | Values outside the approved workflow states |

## Notes on the Great Expectations Implementation

Two of the checks (hours-to-pay reconciliation and approval sequencing) are
cross-column business rules that don't map to a single built-in GX
expectation. Rather than skip them, they're precomputed as derived boolean
columns (`pay_reconciles`, `approval_sequence_valid`) and validated
directly. This is a deliberate, common pattern in real data quality work:
not every business rule has a matching built-in check, so you engineer the
column that expresses it and validate that instead.

## Limitations and Honest Scope

This is a portfolio project built on synthetic data, not a production
pipeline. It does not include: a persistent GX Data Context wired into an
orchestrator, alerting on failure, incremental/streaming validation, or a
CI/CD step that runs the suite automatically on new data. Those would be
the logical next additions in a production setting, and are called out
here deliberately rather than implied as already built.

## Data Disclosure

All data in this project is synthetically generated for demonstration
purposes. No real employee, student, intern, or institutional data is
used or represented.

## Licences

MIT License

Copyright (c) 2026 Alexis Prieto

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
