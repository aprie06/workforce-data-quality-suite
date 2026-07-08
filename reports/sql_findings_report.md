# SQL Data Quality Findings Report

Each section below corresponds to a named check in `sql/validation_queries.sql`. Row counts reflect what the query found against the current dataset.

## 1. Duplicate record_id

**Rows returned:** 12

(showing first 5 of 12 rows)

| record_id | occurrence_count |
|:---|---:|
| TS-002473 | 2 |
| TS-001918 | 2 |
| TS-001415 | 2 |
| TS-001115 | 2 |
| TS-000945 | 2 |

## 2. Missing required fields (hourly_rate, campus)

**Rows returned:** 53

(showing first 5 of 53 rows)

| record_id | employee_id | campus | hourly_rate |
|:---|---:|---:|---:|
| TS-002372 | EMP-1456 | Campus D | nan |
| TS-001827 | EMP-1419 | Campus A | nan |
| TS-001345 | EMP-1709 | Campus E | nan |
| TS-001960 | EMP-1637 | Campus D | nan |
| TS-001030 | EMP-1704 | Campus C | nan |

## 3. Hours worked outside a valid range

**Rows returned:** 34

(showing first 5 of 34 rows)

| record_id | employee_id | hours_worked | issue_type |
|:---|---:|---:|---:|
| TS-002383 | EMP-1464 | 65.13 | exceeds_realistic_cap |
| TS-001507 | EMP-1745 | 89.64 | exceeds_realistic_cap |
| TS-001342 | EMP-1207 | 100.25 | exceeds_realistic_cap |
| TS-001992 | EMP-1046 | -4.47 | negative_or_zero |
| TS-001688 | EMP-1593 | -9.82 | negative_or_zero |

## 4. Hourly rate below minimum wage

**Rows returned:** 25

(showing first 5 of 25 rows)

| record_id | employee_id | hourly_rate |
|:---|---:|---:|
| TS-001242 | EMP-1317 | 5.11 |
| TS-002100 | EMP-1625 | 5.61 |
| TS-001611 | EMP-1567 | 6.92 |
| TS-000596 | EMP-1696 | 4.62 |
| TS-001742 | EMP-1549 | 5.64 |

## 5. Pay reconciliation mismatch

**Rows returned:** 106

(showing first 5 of 106 rows)

| record_id | employee_id | hours_worked | hourly_rate | calculated_pay | expected_pay | variance |
|:---|---:|---:|---:|---:|---:|---:|
| TS-000762 | EMP-1676 | 38.25 | 26.94 | 96.84 | 1030.46 | -933.62 |
| TS-000225 | EMP-1112 | 38.22 | 24.78 | 62.38 | 947.09 | -884.71 |
| TS-001976 | EMP-1107 | 33.69 | 27.98 | 99.16 | 942.65 | -843.49 |
| TS-002061 | EMP-1543 | 35.18 | 29.18 | 198.85 | 1026.55 | -827.7 |
| TS-000466 | EMP-1040 | 27.98 | 27.89 | 47.94 | 780.36 | -732.42 |

## 6. Approval sequencing errors (approved before submitted)

**Rows returned:** 18

(showing first 5 of 18 rows)

| record_id | employee_id | submitted_date | approved_date | days_variance |
|:---|---:|---:|---:|---:|
| TS-001122 | EMP-1748 | 2026-06-09 | 2026-06-01 | -8 |
| TS-001162 | EMP-1291 | 2026-03-13 | 2026-03-05 | -8 |
| TS-001837 | EMP-1196 | 2026-01-14 | 2026-01-08 | -6 |
| TS-000752 | EMP-1248 | 2026-04-03 | 2026-04-01 | -2 |
| TS-002045 | EMP-1712 | 2026-04-04 | 2026-03-30 | -5 |

## 7. Invalid campus code (referential integrity)

**Rows returned:** 10

(showing first 5 of 10 rows)

| record_id | employee_id | campus |
|:---|---:|---:|
| TS-000800 | EMP-1371 | Campus Z |
| TS-000337 | EMP-1472 | Campus Z |
| TS-000273 | EMP-1357 | Campus Z |
| TS-002300 | EMP-1085 | Campus Z |
| TS-000373 | EMP-1716 | Campus Z |

## 8. Invalid pay_status values

**Rows returned:** 8

(showing first 5 of 8 rows)

| record_id | employee_id | pay_status |
|:---|---:|---:|
| TS-001464 | EMP-1447 | Unknown |
| TS-000539 | EMP-1744 | Unknown |
| TS-001160 | EMP-1667 | Unknown |
| TS-000871 | EMP-1012 | Unknown |
| TS-000779 | EMP-1053 | Unknown |

## Summary

| Check | Rows Flagged |
|:---|---:|
| 1. Duplicate record_id | 12 |
| 2. Missing required fields (hourly_rate, campus) | 53 |
| 3. Hours worked outside a valid range | 34 |
| 4. Hourly rate below minimum wage | 25 |
| 5. Pay reconciliation mismatch | 106 |
| 6. Approval sequencing errors (approved before submitted) | 18 |
| 7. Invalid campus code (referential integrity) | 10 |
| 8. Invalid pay_status values | 8 |
