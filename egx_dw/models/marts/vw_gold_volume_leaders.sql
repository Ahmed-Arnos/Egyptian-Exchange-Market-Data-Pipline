{{
  config(
    materialized='view',
    tags=['gold', 'grafana']
  )
}}

-- Volume leaders for today
SELECT 
    symbol,
    close_price,
    volume,
    volume_ma_7d,
    ROUND((volume / NULLIF(volume_ma_7d, 0)) * 100, 2) as volume_vs_avg_pct,
    volume_signal
FROM {{ ref('gold_fct_stock_daily_prices') }}
QUALIFY ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date DESC) = 1
ORDER BY volume DESC
