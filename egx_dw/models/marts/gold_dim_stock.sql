{{
  config(
    materialized='table',
    tags=['gold', 'dimension']
  )
}}

SELECT 
    symbol,
    MIN(trade_date) as first_trade_date,
    MAX(trade_date) as last_trade_date,
    COUNT(DISTINCT trade_date) as total_trading_days,
    'EGX30' as index_membership,  -- Default, can be enhanced later
    TRUE as is_active,
    CURRENT_TIMESTAMP() as created_at,
    CURRENT_TIMESTAMP() as updated_at
FROM {{ ref('stg_stock_prices_unified') }}
WHERE is_complete = TRUE
GROUP BY symbol
