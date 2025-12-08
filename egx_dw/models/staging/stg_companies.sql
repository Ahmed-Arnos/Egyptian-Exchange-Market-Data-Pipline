{{
  config(
    materialized='table'
  )
}}

-- Staging for company master data with enrichments
SELECT 
    company_id,
    symbol,
    company_name,
    sector,
    industry,
    market_cap,
    logo_url,
    analyst_rating,
    is_active,
    created_at,
    updated_at
FROM {{ source('operational', 'TBL_COMPANY') }}
WHERE symbol IS NOT NULL
