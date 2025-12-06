{{
  config(
    materialized='incremental',
    unique_key=['symbol', 'trade_datetime'],
    on_schema_change='sync_all_columns'
  )
}}

-- UDF for parsing volume strings (K/M notation)
{% if target.name == 'dev' and not execute %}
  {{ log("Creating parse_volume_string UDF", info=True) }}
{% endif %}

WITH historical_data AS (
    SELECT 
        symbol,
        TRY_TO_DATE(date_str, 'MM/DD/YYYY') as trade_date,
        TRY_TO_TIMESTAMP(date_str || ' 16:00:00', 'MM/DD/YYYY HH24:MI:SS') as trade_datetime,
        open as open_price,
        high as high_price,
        low as low_price,
        price as close_price,
        -- Parse volume string (2.55M → 2550000)
        CASE 
            WHEN volume_str IS NULL THEN NULL
            WHEN UPPER(volume_str) LIKE '%M%' THEN 
                TRY_CAST(REPLACE(UPPER(volume_str), 'M', '') AS NUMBER) * 1000000
            WHEN UPPER(volume_str) LIKE '%K%' THEN 
                TRY_CAST(REPLACE(UPPER(volume_str), 'K', '') AS NUMBER) * 1000
            WHEN UPPER(volume_str) LIKE '%B%' THEN 
                TRY_CAST(REPLACE(UPPER(volume_str), 'B', '') AS NUMBER) * 1000000000
            ELSE 
                TRY_CAST(volume_str AS NUMBER)
        END as volume,
        TRY_CAST(REPLACE(change_pct, '%', '') AS NUMBER(10, 4)) as change_pct,
        'HISTORICAL' as data_source,
        CASE 
            WHEN open IS NOT NULL 
             AND high IS NOT NULL 
             AND low IS NOT NULL 
             AND price IS NOT NULL 
             AND volume_str IS NOT NULL 
            THEN TRUE 
            ELSE FALSE 
        END as is_complete,
        CASE 
            WHEN high < low THEN TRUE  -- Impossible: high < low
            WHEN price < low OR price > high THEN TRUE  -- Close outside range
            WHEN open < low OR open > high THEN TRUE  -- Open outside range
            ELSE FALSE
        END as has_anomaly,
        'bronze_stock_prices_historical' as bronze_source_table,
        source_file as bronze_source_file,
        ingestion_timestamp
    FROM {{ source('bronze', 'bronze_stock_prices_historical') }}
    WHERE TRY_TO_DATE(date_str, 'MM/DD/YYYY') IS NOT NULL
      AND symbol IS NOT NULL
    {% if is_incremental() %}
      AND ingestion_timestamp > (SELECT MAX(processed_at) FROM {{ this }})
    {% endif %}
),

streaming_data AS (
    SELECT 
        symbol,
        DATE(datetime) as trade_date,
        datetime as trade_datetime,
        open as open_price,
        high as high_price,
        low as low_price,
        close as close_price,
        volume,
        NULL as change_pct,  -- Not in streaming data
        'STREAMING' as data_source,
        CASE 
            WHEN open IS NOT NULL 
             AND high IS NOT NULL 
             AND low IS NOT NULL 
             AND close IS NOT NULL 
             AND volume IS NOT NULL 
            THEN TRUE 
            ELSE FALSE 
        END as is_complete,
        CASE 
            WHEN high < low THEN TRUE
            WHEN close < low OR close > high THEN TRUE
            WHEN open < low OR open > high THEN TRUE
            ELSE FALSE
        END as has_anomaly,
        'bronze_stock_prices_streaming' as bronze_source_table,
        source_file as bronze_source_file,
        ingestion_timestamp
    FROM {{ source('bronze', 'bronze_stock_prices_streaming') }}
    WHERE datetime IS NOT NULL
      AND symbol IS NOT NULL
    {% if is_incremental() %}
      AND ingestion_timestamp > (SELECT MAX(processed_at) FROM {{ this }})
    {% endif %}
),

unified AS (
    SELECT * FROM historical_data
    UNION ALL
    SELECT * FROM streaming_data
)

SELECT 
    symbol,
    trade_date,
    trade_datetime,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    change_pct,
    data_source,
    is_complete,
    has_anomaly,
    bronze_source_table,
    bronze_source_file,
    CURRENT_TIMESTAMP() as processed_at
FROM unified
