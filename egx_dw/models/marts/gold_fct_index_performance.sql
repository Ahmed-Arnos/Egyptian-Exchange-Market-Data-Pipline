-- EGX Index Performance (EGX30, EGX70, EGX100)
-- Calculates weighted index values based on constituent prices
{{
    config(
        materialized='incremental',
        unique_key=['index_code', 'trade_date'],
        tags=['gold', 'fact', 'indices']
    )
}}

WITH index_constituents AS (
    SELECT 
        index_code,
        index_name,
        symbol,
        weight,
        effective_date
    FROM {{ ref('stg_index_membership') }}
),

stock_prices AS (
    SELECT 
        symbol,
        trade_date,
        open_price,
        high_price,
        low_price,
        close_price,
        volume
    FROM {{ ref('stg_stock_prices_unified') }}
    {% if is_incremental() %}
    WHERE trade_date > (SELECT MAX(trade_date) FROM {{ this }})
    {% endif %}
),

-- Join prices with index constituents
index_prices AS (
    SELECT 
        ic.index_code,
        ic.index_name,
        sp.trade_date,
        sp.symbol,
        sp.open_price,
        sp.high_price,
        sp.low_price,
        sp.close_price,
        sp.volume,
        ic.weight,
        
        
        -- Weighted prices
        sp.open_price * ic.weight AS weighted_open,
        sp.high_price * ic.weight AS weighted_high,
        sp.low_price * ic.weight AS weighted_low,
        sp.close_price * ic.weight AS weighted_close,
        sp.volume AS constituent_volume
        
    FROM index_constituents ic
    INNER JOIN stock_prices sp 
        ON ic.symbol = sp.symbol
        AND sp.trade_date >= ic.effective_date
),

-- Calculate index values
index_aggregated AS (
    SELECT 
        index_code,
        index_name,
        trade_date,
        
        -- Index OHLC
        SUM(weighted_open) AS index_open,
        MAX(weighted_high) AS index_high,
        MIN(weighted_low) AS index_low,
        SUM(weighted_close) AS index_close,
        
        -- Aggregate volume
        SUM(constituent_volume) AS total_volume,
        
        -- Constituent count
        COUNT(DISTINCT symbol) AS constituents_count,
        
        -- Metadata
        CURRENT_TIMESTAMP() AS calculated_at
        
    FROM index_prices
    GROUP BY index_code, index_name, trade_date
),

-- Calculate daily change
index_with_change AS (
    SELECT 
        *,
        
        -- Previous close
        LAG(index_close) OVER (
            PARTITION BY index_code 
            ORDER BY trade_date
        ) AS prev_close,
        
        -- Daily change
        index_close - LAG(index_close) OVER (
            PARTITION BY index_code 
            ORDER BY trade_date
        ) AS daily_change,
        
        -- Daily change percent
        CASE 
            WHEN LAG(index_close) OVER (PARTITION BY index_code ORDER BY trade_date) > 0 
            THEN (
                (index_close - LAG(index_close) OVER (PARTITION BY index_code ORDER BY trade_date)) 
                / LAG(index_close) OVER (PARTITION BY index_code ORDER BY trade_date)
            ) * 100
            ELSE NULL
        END AS daily_change_pct,
        
        -- Intraday range
        index_high - index_low AS intraday_range,
        CASE 
            WHEN index_low > 0 
            THEN ((index_high - index_low) / index_low) * 100
            ELSE NULL
        END AS intraday_range_pct
        
    FROM index_aggregated
)

SELECT * FROM index_with_change
