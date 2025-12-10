{{ config(
    materialized='table',
    schema='GOLD'
) }}

WITH base AS (
    SELECT
        symbol,
        company_name,
        currency,
        sector,
        industry,
        headquarters,
        ceo_name,
        website,
        founded_date,
        isin
    FROM {{ ref('stg_companies') }}
),

joined AS (
    SELECT
        b.symbol,
        b.company_name,
        cur.currency_id,
        sec.sector_id,
        ind.industry_id,
        loc.location_id,
        b.ceo_name,
        b.website,
        b.founded_date,
        b.isin
    FROM base b
    LEFT JOIN {{ ref('dim_currency') }} cur
        ON UPPER(TRIM(b.currency)) = cur.currency_code
    LEFT JOIN {{ ref('dim_sector') }} sec
        ON UPPER(TRIM(b.sector)) = sec.sector_name
    LEFT JOIN {{ ref('dim_industry') }} ind
        ON UPPER(TRIM(b.industry)) = ind.industry_name
    LEFT JOIN {{ ref('dim_location') }} loc
        ON UPPER(TRIM(REPLACE(REPLACE(REPLACE(b.headquarters, ',', ' '), '-', ' '), '.', ' ')))
           = loc.location_name
)

SELECT    
    symbol,
    company_name,
    currency_id,
    sector_id,
    industry_id,
    location_id,
    ceo_name,
    website,
    founded_date,
    isin
FROM joined
