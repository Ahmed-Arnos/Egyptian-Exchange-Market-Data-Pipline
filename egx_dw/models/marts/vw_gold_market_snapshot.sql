{{
  config(
    materialized='view',
    tags=['gold', 'grafana']
  )
}}

-- Latest market snapshot for live dashboard
SELECT 
    d.symbol,
    d.company_name,
    d.sector,
    f.trade_date,
    f.close_price as current_price,
    f.price_change,
    f.price_change_pct,
    f.volume,
    f.high_price as day_high,
    f.low_price as day_low,
    f.ma_7d,
    f.ma_30d,
    f.trend_signal,
    f.volume_signal,
    d.pe_ratio,
    d.market_cap,
    d.analyst_rating,
    f.data_source
FROM {{ ref('gold_fct_stock_daily_prices') }} f
JOIN {{ ref('gold_dim_company') }} d 
    ON f.symbol = d.symbol
QUALIFY ROW_NUMBER() OVER (PARTITION BY f.symbol ORDER BY f.trade_date DESC) = 1
