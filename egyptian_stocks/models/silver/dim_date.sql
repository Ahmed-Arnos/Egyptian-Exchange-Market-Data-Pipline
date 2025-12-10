{{ config(
    materialized='table',
    schema='GOLD'
) }}

WITH dates AS (
    SELECT
        DATEADD(day, SEQ4(), '2000-01-01') AS date_day
    FROM TABLE(GENERATOR(ROWCOUNT => 365 * 50))
)

SELECT
    TO_NUMBER(TO_CHAR(date_day, 'YYYYMMDD')) AS date_id,
    date_day AS date,
    YEAR(date_day) AS year,
    MONTH(date_day) AS month,
    DAY(date_day) AS day,
    WEEK(date_day) AS week,
    QUARTER(date_day) AS quarter,
    TO_CHAR(date_day, 'YYYY-MM') AS year_month,
    TO_CHAR(date_day, 'YYYY-Q') AS year_quarter,
    DAYNAME(date_day) AS day_name,
       CASE 
        WHEN DAYOFWEEK(date_day) IN (5, 6) THEN TRUE
        ELSE FALSE
    END AS is_weekend,
        CASE
        WHEN MONTH(date_day) >= 7 THEN YEAR(date_day) + 1
        ELSE YEAR(date_day)
    END AS fiscal_year,
    CASE
        WHEN MONTH(date_day) IN (1,2,3) THEN 4
        WHEN MONTH(date_day) IN (4,5,6) THEN 1
        WHEN MONTH(date_day) IN (7,8,9) THEN 2
        ELSE 3
    END AS fiscal_quarter,
    CASE
        WHEN MONTH(date_day) IN (12, 1, 2) THEN 'Winter'
        WHEN MONTH(date_day) IN (3, 4, 5) THEN 'Spring'
        WHEN MONTH(date_day) IN (6, 7, 8) THEN 'Summer'
        WHEN MONTH(date_day) IN (9, 10, 11) THEN 'Autumn'
    END AS season
    

FROM dates
ORDER BY date_day