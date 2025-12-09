{{
  config(
    materialized='table'
  )
}}

-- Staging for company master data with enrichments and null handling
SELECT 
    company_id,
    COALESCE(symbol, 'UNKNOWN') as symbol,
    COALESCE(company_name, 'Unknown Company') as company_name,
    COALESCE(sector, 'Unclassified') as sector,
    COALESCE(industry, 'Unknown') as industry,
    COALESCE(market_cap, 0) as market_cap,
    logo_url,
    COALESCE(analyst_rating, 'Not Rated') as analyst_rating,
    COALESCE(is_active, TRUE) as is_active,
    created_at,
    updated_at
FROM {{ source('operational', 'TBL_COMPANY') }}
WHERE symbol IS NOT NULL
