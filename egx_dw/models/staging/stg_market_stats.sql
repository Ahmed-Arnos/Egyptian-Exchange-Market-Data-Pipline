{{
  config(
    materialized='incremental',
    unique_key=['company_id', 'snapshot_datetime']
  )
}}

-- Staging for market statistics with company info
-- Latest snapshot per company for most recent data
SELECT 
    m.stat_id,
    m.company_id,
    c.symbol,
    c.company_name,
    c.sector as company_sector,
    m.snapshot_datetime,
    m.price,
    m.change_pct,
    m.volume,
    m.relative_volume,
    m.market_cap,
    m.pe_ratio,
    m.eps_ttm,
    m.eps_growth_yoy,
    m.div_yield_pct,
    m.sector as market_sector,
    m.analyst_rating,
    -- Use market_sector if company_sector is null
    COALESCE(c.sector, m.sector) as effective_sector,
    m.created_at as ingested_at,
    CURRENT_TIMESTAMP() as updated_at
FROM {{ source('operational', 'TBL_MARKET_STAT') }} m
INNER JOIN {{ source('operational', 'TBL_COMPANY') }} c 
    ON m.company_id = c.company_id
{% if is_incremental() %}
WHERE m.created_at > (SELECT COALESCE(MAX(ingested_at), '1900-01-01'::timestamp) FROM {{ this }})
{% endif %}
