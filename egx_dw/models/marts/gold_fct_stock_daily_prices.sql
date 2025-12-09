{{
  config(
    materialized='incremental',
    unique_key=['symbol', 'trade_date'],
    on_schema_change='sync_all_columns',
    tags=['gold', 'fact']
  )
}}

WITH daily_agg AS (
    -- Already at daily level from staging with guaranteed non-null values
    SELECT 
        symbol,
        trade_date,
        COALESCE(open_price, close_price) as open_price,
        COALESCE(high_price, close_price) as high_price,
        COALESCE(low_price, close_price) as low_price,
        close_price,
        COALESCE(volume, 0) as volume,
        data_source
    FROM {{ ref('stg_stock_prices_unified') }}
    WHERE close_price IS NOT NULL
    {% if is_incremental() %}
      AND trade_date > (SELECT MAX(trade_date) FROM {{ this }})
    {% endif %}
),

with_technical_indicators AS (
    SELECT 
        symbol,
        trade_date,
        open_price,
        high_price,
        low_price,
        close_price,
        volume,
        data_source,
        
        -- Price changes
        close_price - LAG(close_price) OVER (PARTITION BY symbol ORDER BY trade_date) as price_change,
        ROUND(
            ((close_price - LAG(close_price) OVER (PARTITION BY symbol ORDER BY trade_date)) 
             / NULLIF(LAG(close_price) OVER (PARTITION BY symbol ORDER BY trade_date), 0)) * 100, 
            4
        ) as price_change_pct,
        
        -- Price metrics
        high_price - low_price as price_range,
        ROUND((high_price + low_price + close_price) / 3, 2) as typical_price,
        
        -- Moving averages
        ROUND(
            AVG(close_price) OVER (
                PARTITION BY symbol 
                ORDER BY trade_date 
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ), 
            2
        ) as ma_7d,
        ROUND(
            AVG(close_price) OVER (
                PARTITION BY symbol 
                ORDER BY trade_date 
                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ), 
            2
        ) as ma_30d,
        
        -- Volume moving average
        ROUND(
            AVG(volume) OVER (
                PARTITION BY symbol 
                ORDER BY trade_date 
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ), 
            0
        ) as volume_ma_7d
        
    FROM daily_agg
)

SELECT 
    symbol,
    trade_date,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    price_change,
    price_change_pct,
    price_range,
    typical_price,
    ma_7d,
    ma_30d,
    volume_ma_7d,
    
    -- Trend signal
    CASE 
        WHEN ma_7d > ma_30d AND close_price > ma_7d THEN 'BULLISH'
        WHEN ma_7d < ma_30d AND close_price < ma_7d THEN 'BEARISH'
        ELSE 'NEUTRAL'
    END as trend_signal,
    
    -- Volume signal
    CASE 
        WHEN volume > volume_ma_7d * 1.5 THEN 'HIGH'
        WHEN volume < volume_ma_7d * 0.5 THEN 'LOW'
        ELSE 'NORMAL'
    END as volume_signal,
    
    data_source,
    CURRENT_TIMESTAMP() as last_updated
    
FROM with_technical_indicators
