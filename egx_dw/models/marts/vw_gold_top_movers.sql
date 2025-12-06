{{
  config(
    materialized='view',
    tags=['gold', 'grafana']
  )
}}

-- Top gainers and losers for today
SELECT 
    symbol,
    close_price,
    price_change,
    price_change_pct,
    volume,
    trend_signal,
    CASE 
        WHEN price_change_pct > 0 THEN 'GAINER'
        WHEN price_change_pct < 0 THEN 'LOSER'
        ELSE 'UNCHANGED'
    END as mover_type
FROM {{ ref('gold_fct_stock_daily_prices') }}
WHERE price_change_pct IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) = 1
ORDER BY ABS(price_change_pct) DESC
