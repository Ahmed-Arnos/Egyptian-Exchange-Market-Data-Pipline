-- ================================================================
-- SNOWFLAKE S3 INTEGRATION SETUP
-- Purpose: Configure Snowflake to access S3 bucket for data loading
-- ================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE EGX_OPERATIONAL_DB;
USE WAREHOUSE EGX_WH;

-- ================================================================
-- SECTION 1: CREATE STORAGE INTEGRATION (AWS S3)
-- ================================================================

-- This allows Snowflake to access your S3 bucket securely
-- Note: After creating this, you'll need to configure AWS IAM trust policy
CREATE OR REPLACE STORAGE INTEGRATION s3_egx_integration
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'S3'
  ENABLED = TRUE
  STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::622718430464:role/snowflake-s3-access-role'
  STORAGE_ALLOWED_LOCATIONS = ('s3://egx-data-bucket/batch/', 's3://egx-data-bucket/streaming/');

-- Get the AWS IAM User ARN and External ID for AWS trust policy setup
DESC STORAGE INTEGRATION s3_egx_integration;

-- ================================================================
-- SECTION 2: CREATE FILE FORMATS
-- ================================================================

-- File format for historical CSV data from batch/
CREATE OR REPLACE FILE FORMAT csv_format_egx
  TYPE = 'CSV'
  FIELD_DELIMITER = ','
  RECORD_DELIMITER = '\n'
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  TRIM_SPACE = TRUE
  ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
  DATE_FORMAT = 'MM/DD/YYYY'
  NULL_IF = ('NULL', 'null', '');

-- File format for streaming JSON data
CREATE OR REPLACE FILE FORMAT json_format_egx
  TYPE = 'JSON'
  STRIP_OUTER_ARRAY = FALSE
  DATE_FORMAT = 'AUTO'
  TIME_FORMAT = 'AUTO'
  TIMESTAMP_FORMAT = 'AUTO';

-- ================================================================
-- SECTION 3: CREATE EXTERNAL STAGES
-- ================================================================

-- Stage for historical batch data (CSV files)
CREATE OR REPLACE STAGE s3_stage_batch
  STORAGE_INTEGRATION = s3_egx_integration
  URL = 's3://egx-data-bucket/batch/'
  FILE_FORMAT = csv_format_egx;

-- Stage for real-time streaming data (JSON files)
CREATE OR REPLACE STAGE s3_stage_streaming
  STORAGE_INTEGRATION = s3_egx_integration
  URL = 's3://egx-data-bucket/streaming/'
  FILE_FORMAT = json_format_egx;

-- ================================================================
-- SECTION 4: CREATE BRONZE SCHEMA (RAW DATA LANDING)
-- ================================================================

CREATE SCHEMA IF NOT EXISTS BRONZE;
USE SCHEMA BRONZE;

-- Bronze table for historical data (CSV from batch/)
CREATE OR REPLACE TABLE bronze_stock_prices_historical (
    date_str VARCHAR(50),
    price NUMBER(10, 2),
    open NUMBER(10, 2),
    high NUMBER(10, 2),
    low NUMBER(10, 2),
    volume_str VARCHAR(50),  -- Keep as string initially (contains 'M', 'K')
    change_pct VARCHAR(20),
    symbol VARCHAR(20),
    -- Metadata
    source_file VARCHAR(500),
    ingestion_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    partition_date DATE
);

-- Bronze table for streaming data (JSON from streaming/)
CREATE OR REPLACE TABLE bronze_stock_prices_streaming (
    raw_data VARIANT,  -- Store full JSON
    symbol VARCHAR(20),
    exchange VARCHAR(20),
    interval VARCHAR(20),
    datetime TIMESTAMP_NTZ,
    open NUMBER(10, 2),
    high NUMBER(10, 2),
    low NUMBER(10, 2),
    close NUMBER(10, 2),
    volume NUMBER,
    -- Metadata
    source_file VARCHAR(500),
    ingestion_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    partition_date DATE
);

-- ================================================================
-- SECTION 5: TEST STAGES (Verify S3 connectivity)
-- ================================================================

-- List files in batch stage
LIST @s3_stage_batch;

-- List files in streaming stage  
LIST @s3_stage_streaming;

-- Test query batch data (first 10 rows from one file)
SELECT 
    $1 as date_str,
    $2 as price,
    $3 as open,
    $4 as high,
    $5 as low,
    $6 as volume_str,
    $7 as change_pct,
    $8 as symbol
FROM @s3_stage_batch/EGX30/EGX30/COMI/COMI.csv
LIMIT 10;

-- Test query streaming data (first 10 JSON records)
SELECT 
    $1 as raw_json,
    $1:symbol::STRING as symbol,
    $1:datetime::TIMESTAMP_NTZ as datetime,
    $1:close::NUMBER(10,2) as close,
    $1:volume::NUMBER as volume
FROM @s3_stage_streaming
LIMIT 10;

-- ================================================================
-- SECTION 6: VALIDATION QUERIES
-- ================================================================

-- Check storage integration
SHOW STORAGE INTEGRATIONS;

-- Check file formats
SHOW FILE FORMATS;

-- Check stages
SHOW STAGES;

-- Check tables
SHOW TABLES IN SCHEMA BRONZE;
