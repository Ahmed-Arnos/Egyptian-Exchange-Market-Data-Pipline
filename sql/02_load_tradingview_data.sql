-- ================================================================
-- LOAD TRADINGVIEW DATA INTO OPERATIONAL DATABASE
-- Purpose: Migrate existing EGX_DB.RAW.egx30_history_data to operational schema
-- ================================================================

USE DATABASE EGX_OPERATIONAL_DB;
USE SCHEMA OPERATIONAL;

-- ================================================================
-- STEP 1: Load stocks from historical data
-- ================================================================

-- Insert unique stock symbols from raw data
INSERT INTO stocks (symbol, company_name, is_active)
SELECT DISTINCT
    stock_symbol AS symbol,
    stock_symbol AS company_name,  -- Will update with actual names later
    TRUE AS is_active
FROM EGX_DB.RAW.egx30_history_data
WHERE stock_symbol IS NOT NULL
ON CONFLICT (symbol) DO NOTHING;

-- Verify stocks loaded
SELECT 'Stocks loaded: ' || COUNT(*) AS result FROM stocks;

-- ================================================================
-- STEP 2: Load historical stock prices
-- ================================================================

-- Start ETL log
INSERT INTO data_load_log (source_name, load_type, start_time, status)
VALUES ('TradingView_Historical', 'BATCH', CURRENT_TIMESTAMP(), 'RUNNING');

-- Get the load_id for tracking
SET load_id = (SELECT MAX(load_id) FROM data_load_log);

-- Load prices with transformation
INSERT INTO stock_prices_daily (
    stock_id,
    trade_date,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    source
)
SELECT 
    s.stock_id,
    raw.trade_date,
    raw.open_price,
    raw.high_price,
    raw.low_price,
    raw.closing_price AS close_price,
    -- Convert volume from string with K/M notation to number
    CASE 
        WHEN raw.volume LIKE '%M' THEN 
            TRY_CAST(REPLACE(raw.volume, 'M', '') AS DECIMAL(18,2)) * 1000000
        WHEN raw.volume LIKE '%K' THEN 
            TRY_CAST(REPLACE(raw.volume, 'K', '') AS DECIMAL(18,2)) * 1000
        ELSE 
            TRY_CAST(raw.volume AS BIGINT)
    END AS volume,
    'TradingView' AS source
FROM EGX_DB.RAW.egx30_history_data raw
JOIN stocks s ON raw.stock_symbol = s.symbol
WHERE raw.trade_date IS NOT NULL
  AND raw.closing_price IS NOT NULL
ON CONFLICT (stock_id, trade_date) DO NOTHING;

-- Update ETL log
UPDATE data_load_log
SET 
    end_time = CURRENT_TIMESTAMP(),
    records_loaded = (SELECT COUNT(*) FROM stock_prices_daily WHERE source = 'TradingView'),
    status = 'SUCCESS'
WHERE load_id = $load_id;

-- Verify data loaded
SELECT 
    'Historical prices loaded: ' || COUNT(*) AS result,
    'Date range: ' || MIN(trade_date) || ' to ' || MAX(trade_date) AS date_range,
    'Stocks: ' || COUNT(DISTINCT stock_id) AS stocks
FROM stock_prices_daily;

-- ================================================================
-- STEP 3: Assign EGX30 index membership
-- ================================================================

-- Get or create EGX30 index ID
SET egx30_index_id = (SELECT index_id FROM indices WHERE index_code = 'EGX30');

-- Insert current EGX30 constituents (all stocks from historical data are EGX30)
INSERT INTO index_constituents (
    index_id,
    stock_id,
    weight,
    effective_date,
    end_date
)
SELECT 
    $egx30_index_id AS index_id,
    s.stock_id,
    1.0 / (SELECT COUNT(DISTINCT stock_id) FROM stocks) AS weight,  -- Equal weight for now
    '2020-01-01'::DATE AS effective_date,
    NULL AS end_date  -- Currently active
FROM stocks s
ON CONFLICT (index_id, stock_id, effective_date) DO NOTHING;

-- Verify constituents
SELECT 'EGX30 constituents: ' || COUNT(*) AS result 
FROM index_constituents 
WHERE index_id = $egx30_index_id AND end_date IS NULL;

-- ================================================================
-- STEP 4: Data quality checks
-- ================================================================

-- Check for data quality issues
SELECT 
    'Quality Check: Null prices' AS check_name,
    COUNT(*) AS issue_count
FROM stock_prices_daily
WHERE close_price IS NULL OR close_price <= 0

UNION ALL

SELECT 
    'Quality Check: Invalid high/low' AS check_name,
    COUNT(*) AS issue_count
FROM stock_prices_daily
WHERE high_price < low_price

UNION ALL

SELECT 
    'Quality Check: Negative volumes' AS check_name,
    COUNT(*) AS issue_count
FROM stock_prices_daily
WHERE volume < 0;

-- ================================================================
-- STEP 5: Summary statistics
-- ================================================================

SELECT '=== OPERATIONAL DATABASE SUMMARY ===' AS summary;

SELECT 
    'Total Stocks' AS metric,
    COUNT(*) AS value
FROM stocks

UNION ALL

SELECT 
    'Active Stocks' AS metric,
    COUNT(*) AS value
FROM stocks WHERE is_active = TRUE

UNION ALL

SELECT 
    'Total Price Records' AS metric,
    COUNT(*) AS value
FROM stock_prices_daily

UNION ALL

SELECT 
    'Date Range (Days)' AS metric,
    DATEDIFF(day, MIN(trade_date), MAX(trade_date)) AS value
FROM stock_prices_daily

UNION ALL

SELECT 
    'Indices Configured' AS metric,
    COUNT(*) AS value
FROM indices

UNION ALL

SELECT 
    'Index Constituents' AS metric,
    COUNT(*) AS value
FROM index_constituents WHERE end_date IS NULL;

-- ================================================================
-- STEP 6: Create summary view for verification
-- ================================================================

CREATE OR REPLACE VIEW vw_load_summary AS
SELECT 
    s.symbol,
    s.company_name,
    COUNT(spd.price_id) AS total_records,
    MIN(spd.trade_date) AS first_date,
    MAX(spd.trade_date) AS last_date,
    ROUND(AVG(spd.close_price), 2) AS avg_price,
    ROUND(MIN(spd.close_price), 2) AS min_price,
    ROUND(MAX(spd.close_price), 2) AS max_price,
    SUM(spd.volume) AS total_volume
FROM stocks s
LEFT JOIN stock_prices_daily spd ON s.stock_id = spd.stock_id
GROUP BY s.symbol, s.company_name
ORDER BY total_records DESC;

-- Display summary
SELECT * FROM vw_load_summary;

SELECT 'Data Load Complete!' AS status;
