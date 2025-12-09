{{
  config(
    materialized='incremental',
    unique_key=['symbol', 'trade_date', 'data_source']
  )
}}

-- Unified staging from OPERATIONAL.TBL_STOCK_PRICE with company info
SELECT 
    c.symbol,
    c.company_name,
    c.sector,
    p.trade_date,
    p.open_price,
    p.high_price,
    p.low_price,
    p.close_price,
    p.volume,
    p.change_pct,
    p.data_source,
    p.created_at as ingested_at,
    CURRENT_TIMESTAMP() as updated_at
FROM {{ source('operational', 'TBL_STOCK_PRICE') }} p
INNER JOIN {{ source('operational', 'TBL_COMPANY') }} c 
    ON p.company_id = c.company_id
WHERE p.trade_date IS NOT NULL
  AND p.close_price IS NOT NULL
{% if is_incremental() %}
  AND p.created_at > (SELECT COALESCE(MAX(ingested_at), '1900-01-01'::timestamp) FROM {{ this }})
{% endif %}
