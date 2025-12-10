{{ config(materialized='table',schema='GOLD') }}

WITH distinct_industries AS (
    SELECT DISTINCT
        UPPER(TRIM(industry)) AS industry_name
    FROM {{ ref('stg_companies') }}
    WHERE industry IS NOT NULL AND TRIM(industry) <> ''
)

SELECT
    ROW_NUMBER() OVER (ORDER BY industry_name) AS industry_id,
    industry_name
FROM distinct_industries
ORDER BY industry_name