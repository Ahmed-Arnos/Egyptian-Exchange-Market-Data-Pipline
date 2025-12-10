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
    date_day AS date,
    YEAR(date_day) AS year,
    MONTH(date_day) AS month,
    DAY(date_day) AS day,
    WEEK(date_day) AS week,
    QUARTER(date_day) AS quarter,
    TO_CHAR(date_day, 'YYYY-MM') AS year_month,
    TO_CHAR(date_day, 'YYYY-Q') AS year_quarter,
    DAYNAME(date_day) AS day_name,
    CASE WHEN DAYOFWEEK(date_day) IN (1,7) THEN TRUE ELSE FALSE END AS is_weekend
FROM dates
