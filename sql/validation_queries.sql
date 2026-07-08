-- =============================================================================
-- validation_queries.sql
--
-- Data quality validation layer for the timesheets table. Each query
-- isolates one category of defect and returns the offending rows so an
-- analyst can review and remediate, not just a pass/fail count.
--
-- Written and tested against SQLite. Portable to Postgres/Snowflake/SQL
-- Server with the syntax notes called out inline where relevant.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Duplicate record_id
-- A record_id should be a unique primary key. Duplicates indicate a
-- re-submission or batch upload error and will double-count pay if not
-- caught before the approval cycle closes.
-- -----------------------------------------------------------------------------
SELECT
    record_id,
    COUNT(*) AS occurrence_count
FROM timesheets
GROUP BY record_id
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC;


-- -----------------------------------------------------------------------------
-- 2. Missing required fields (hourly_rate, campus)
-- These fields are required to clear an approval cycle. A NULL here means
-- the record cannot be paid as-is and needs to route back for correction.
-- -----------------------------------------------------------------------------
SELECT
    record_id,
    employee_id,
    campus,
    hourly_rate
FROM timesheets
WHERE hourly_rate IS NULL
   OR campus IS NULL
   OR TRIM(campus) = '';


-- -----------------------------------------------------------------------------
-- 3. Hours worked outside a valid range
-- Negative or zero hours are logically invalid. Hours above a realistic
-- cap for a part-time role in a single pay period point to a data entry
-- error (e.g. a misplaced decimal) rather than an actual hours-worked value.
-- -----------------------------------------------------------------------------
SELECT
    record_id,
    employee_id,
    hours_worked,
    CASE
        WHEN hours_worked <= 0 THEN 'negative_or_zero'
        WHEN hours_worked > 40 THEN 'exceeds_realistic_cap'
    END AS issue_type
FROM timesheets
WHERE hours_worked <= 0
   OR hours_worked > 40;


-- -----------------------------------------------------------------------------
-- 4. Hourly rate below the applicable minimum wage
-- A rate below the statutory floor is either a compliance violation or
-- a data entry error and must be flagged before payment, not after.
-- -----------------------------------------------------------------------------
SELECT
    record_id,
    employee_id,
    hourly_rate
FROM timesheets
WHERE hourly_rate IS NOT NULL
  AND hourly_rate < 7.25;


-- -----------------------------------------------------------------------------
-- 5. Pay reconciliation
-- calculated_pay should equal hours_worked * hourly_rate within a small
-- rounding tolerance. A mismatch beyond that tolerance means the pay
-- amount was overridden, miscalculated, or corrupted somewhere upstream.
-- -----------------------------------------------------------------------------
SELECT
    record_id,
    employee_id,
    hours_worked,
    hourly_rate,
    calculated_pay,
    ROUND(hours_worked * hourly_rate, 2) AS expected_pay,
    ROUND(calculated_pay - (hours_worked * hourly_rate), 2) AS variance
FROM timesheets
WHERE hourly_rate IS NOT NULL
  AND ABS(calculated_pay - (hours_worked * hourly_rate)) > 0.02
ORDER BY ABS(calculated_pay - (hours_worked * hourly_rate)) DESC;


-- -----------------------------------------------------------------------------
-- 6. Approval sequencing errors
-- approved_date should never be earlier than submitted_date. This
-- indicates either a workflow bug or a manually backdated record.
-- -----------------------------------------------------------------------------
SELECT
    record_id,
    employee_id,
    submitted_date,
    approved_date,
    -- julianday() is SQLite-specific; use DATEDIFF() in SQL Server or
    -- (approved_date - submitted_date) directly in Postgres
    CAST(julianday(approved_date) - julianday(submitted_date) AS INTEGER) AS days_variance
FROM timesheets
WHERE approved_date < submitted_date;


-- -----------------------------------------------------------------------------
-- 7. Referential integrity on campus code
-- Every campus value should exist in the valid_campuses reference table.
-- A value that doesn't match indicates a typo or a decommissioned code
-- still present in an upstream source system.
-- -----------------------------------------------------------------------------
SELECT
    t.record_id,
    t.employee_id,
    t.campus
FROM timesheets t
LEFT JOIN valid_campuses v
    ON t.campus = v.campus
WHERE t.campus IS NOT NULL
  AND v.campus IS NULL;


-- -----------------------------------------------------------------------------
-- 8. Invalid pay_status values
-- pay_status should only ever be one of the four approved workflow
-- states. Anything else means a value slipped through from a source
-- system with a different status vocabulary, or a manual override.
-- -----------------------------------------------------------------------------
SELECT
    record_id,
    employee_id,
    pay_status
FROM timesheets
WHERE pay_status NOT IN ('Approved', 'Pending', 'Rejected', 'Processing');


-- -----------------------------------------------------------------------------
-- 9. Summary rollup
-- One row per defect category with a count, intended as the top-level
-- output for a data quality dashboard or a stakeholder-facing summary.
-- -----------------------------------------------------------------------------
SELECT 'duplicate_record_id' AS check_name,
       (SELECT COUNT(*) FROM (
           SELECT record_id FROM timesheets GROUP BY record_id HAVING COUNT(*) > 1
       )) AS failing_rows
UNION ALL
SELECT 'missing_required_field',
       (SELECT COUNT(*) FROM timesheets
        WHERE hourly_rate IS NULL OR campus IS NULL OR TRIM(campus) = '')
UNION ALL
SELECT 'hours_worked_out_of_range',
       (SELECT COUNT(*) FROM timesheets WHERE hours_worked <= 0 OR hours_worked > 40)
UNION ALL
SELECT 'hourly_rate_below_minimum_wage',
       (SELECT COUNT(*) FROM timesheets WHERE hourly_rate IS NOT NULL AND hourly_rate < 7.25)
UNION ALL
SELECT 'pay_reconciliation_mismatch',
       (SELECT COUNT(*) FROM timesheets
        WHERE hourly_rate IS NOT NULL AND ABS(calculated_pay - (hours_worked * hourly_rate)) > 0.02)
UNION ALL
SELECT 'approved_before_submitted',
       (SELECT COUNT(*) FROM timesheets WHERE approved_date < submitted_date)
UNION ALL
SELECT 'invalid_campus_code',
       (SELECT COUNT(*) FROM timesheets t
        LEFT JOIN valid_campuses v ON t.campus = v.campus
        WHERE t.campus IS NOT NULL AND v.campus IS NULL)
UNION ALL
SELECT 'invalid_pay_status',
       (SELECT COUNT(*) FROM timesheets
        WHERE pay_status NOT IN ('Approved', 'Pending', 'Rejected', 'Processing'));
