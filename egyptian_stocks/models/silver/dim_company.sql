{{ config(
    materialized='table',
    schema='GOLD'
) }}
SELECT
    symbol,
    company_name,
    currency,
    sector,
    industry,
    ceo_name,
    website,
    headquarters,
    TRY_TO_DATE(founded_date) AS founded_date,
    isin,
    MIN(load_ts) AS first_seen_ts,
    MAX(load_ts) AS last_seen_ts
FROM {{ ref('stg_companies') }}
GROUP BY 1,2,3,4,5,6,7,8,9,10
