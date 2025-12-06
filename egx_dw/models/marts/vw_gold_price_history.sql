{{
  config(
    materialized='view',
    tags=['gold', 'grafana']
  )
}}

-- Historical price time series for charts (last 6 months)
SELECT 
    symbol,
    trade_date,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    ma_7d,
    ma_30d,
    trend_signal,
    data_source
FROM {{ ref('gold_fct_stock_daily_prices') }}
WHERE trade_date >= DATEADD(month, -6, CURRENT_DATE())
ORDER BY symbol, trade_date
