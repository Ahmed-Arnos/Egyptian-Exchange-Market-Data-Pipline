-- ================================================================
-- CLEANUP OLD SCHEMAS
-- Purpose: Remove incorrectly named schemas created before dbt macro fix
-- ================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE EGX_OPERATIONAL_DB;
USE WAREHOUSE EGX_WH;

-- Drop old incorrectly named schemas (created with double-prefixing bug)
DROP SCHEMA IF EXISTS SILVER_silver CASCADE;
DROP SCHEMA IF EXISTS SILVER_gold CASCADE;

-- Verify only correct schemas remain
SHOW SCHEMAS IN DATABASE EGX_OPERATIONAL_DB;

-- Verify correct dbt-created schemas exist with data
SELECT 'silver.stg_stock_prices_unified' as table_name, COUNT(*) as row_count 
FROM silver.stg_stock_prices_unified
UNION ALL
SELECT 'gold.gold_fct_stock_daily_prices', COUNT(*) 
FROM gold.gold_fct_stock_daily_prices
UNION ALL
SELECT 'gold.gold_dim_stock', COUNT(*) 
FROM gold.gold_dim_stock
UNION ALL
SELECT 'gold.vw_gold_market_snapshot', COUNT(*) 
FROM gold.vw_gold_market_snapshot;
