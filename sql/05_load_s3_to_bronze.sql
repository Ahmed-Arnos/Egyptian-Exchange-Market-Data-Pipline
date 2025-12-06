-- ================================================================
-- LOAD DATA FROM S3 TO SNOWFLAKE BRONZE LAYER
-- Purpose: Load both historical CSV and streaming JSON data
-- ================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE EGX_OPERATIONAL_DB;
USE WAREHOUSE EGX_WH;
USE SCHEMA BRONZE;

-- ================================================================
-- SECTION 1: LOAD HISTORICAL DATA (CSV from batch/)
-- ================================================================

-- Load all historical CSV files from batch/EGX30/
COPY INTO bronze_stock_prices_historical (
    date_str,
    price,
    open,
    high,
    low,
    volume_str,
    change_pct,
    symbol,
    source_file,
    partition_date
)
FROM (
    SELECT 
        $1,  -- Date
        TRY_CAST($2 AS NUMBER(10, 2)),  -- Price
        TRY_CAST($3 AS NUMBER(10, 2)),  -- Open
        TRY_CAST($4 AS NUMBER(10, 2)),  -- High
        TRY_CAST($5 AS NUMBER(10, 2)),  -- Low
        $6,  -- Volume (keep as string for now)
        $7,  -- Change %
        $8,  -- Symbol
        METADATA$FILENAME,  -- Source file path
        CURRENT_DATE()  -- Partition date
    FROM @s3_stage_batch
)
PATTERN = '.*EGX30/.*/.*\\.csv'
FILE_FORMAT = csv_format_egx
ON_ERROR = CONTINUE;

-- ================================================================
-- SECTION 2: LOAD STREAMING DATA (JSON from streaming/)
-- ================================================================

-- Load all JSON files from streaming/
COPY INTO bronze_stock_prices_streaming (
    raw_data,
    symbol,
    exchange,
    interval,
    datetime,
    open,
    high,
    low,
    close,
    volume,
    source_file,
    partition_date
)
FROM (
    SELECT 
        $1,  -- Full JSON as VARIANT
        $1:symbol::STRING,
        $1:exchange::STRING,
        $1:interval::STRING,
        $1:datetime::TIMESTAMP_NTZ,
        $1:open::NUMBER(10, 2),
        $1:high::NUMBER(10, 2),
        $1:low::NUMBER(10, 2),
        $1:close::NUMBER(10, 2),
        $1:volume::NUMBER,
        METADATA$FILENAME,
        CURRENT_DATE()
    FROM @s3_stage_streaming
)
PATTERN = '.*\\.json'
FILE_FORMAT = json_format_egx
ON_ERROR = CONTINUE;

-- ================================================================
-- SECTION 3: DATA QUALITY CHECKS
-- ================================================================

-- Check historical data load
SELECT 
    'Historical Data (Bronze)' as data_source,
    COUNT(*) as total_records,
    COUNT(DISTINCT symbol) as unique_symbols,
    MIN(TO_DATE(date_str, 'MM/DD/YYYY')) as earliest_date,
    MAX(TO_DATE(date_str, 'MM/DD/YYYY')) as latest_date
FROM bronze_stock_prices_historical;

-- Check streaming data load
SELECT 
    'Streaming Data (Bronze)' as data_source,
    COUNT(*) as total_records,
    COUNT(DISTINCT symbol) as unique_symbols,
    MIN(datetime) as earliest_datetime,
    MAX(datetime) as latest_datetime
FROM bronze_stock_prices_streaming;

-- Sample historical records
SELECT * FROM bronze_stock_prices_historical LIMIT 10;

-- Sample streaming records
SELECT * FROM bronze_stock_prices_streaming LIMIT 10;

-- Check for duplicates in historical data
SELECT 
    symbol,
    date_str,
    COUNT(*) as duplicate_count
FROM bronze_stock_prices_historical
GROUP BY symbol, date_str
HAVING COUNT(*) > 1;

-- Check for duplicates in streaming data
SELECT 
    symbol,
    datetime,
    COUNT(*) as duplicate_count
FROM bronze_stock_prices_streaming
GROUP BY symbol, datetime
HAVING COUNT(*) > 1;
