-- ============================================================================
-- OPERATIONAL DATABASE SCHEMA - Complete Egyptian Stock Market Database
-- Created from scratch based on S3 data sources
-- ============================================================================

-- Drop and recreate database
DROP DATABASE IF EXISTS EGX_OPERATIONAL_DB;
CREATE DATABASE EGX_OPERATIONAL_DB;
USE DATABASE EGX_OPERATIONAL_DB;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS STAGING;      -- Raw data landing
CREATE SCHEMA IF NOT EXISTS OPERATIONAL;  -- Normalized relational DB
CREATE SCHEMA IF NOT EXISTS DWH_SILVER;   -- Data warehouse staging
CREATE SCHEMA IF NOT EXISTS DWH_GOLD;     -- Data warehouse analytics

-- ============================================================================
-- OPERATIONAL SCHEMA - Normalized Tables with PK/FK
-- ============================================================================
USE SCHEMA OPERATIONAL;

-- Companies Master Table
CREATE TABLE TBL_COMPANY (
    company_id INTEGER AUTOINCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    company_name VARCHAR(200),
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap DECIMAL(20,2),
    logo_url VARCHAR(500),
    analyst_rating VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Stock Market Indices
CREATE TABLE TBL_INDEX (
    index_id INTEGER AUTOINCREMENT PRIMARY KEY,
    index_code VARCHAR(20) NOT NULL UNIQUE,
    index_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- Index Membership (Many-to-Many)
CREATE TABLE TBL_INDEX_MEMBERSHIP (
    membership_id INTEGER AUTOINCREMENT PRIMARY KEY,
    index_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    weight DECIMAL(8,4),
    effective_date DATE,
    is_current BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (index_id) REFERENCES TBL_INDEX(index_id),
    FOREIGN KEY (company_id) REFERENCES TBL_COMPANY(company_id),
    UNIQUE (index_id, company_id)
);

-- Stock Prices (OHLCV)
CREATE TABLE TBL_STOCK_PRICE (
    price_id BIGINT AUTOINCREMENT PRIMARY KEY,
    company_id INTEGER NOT NULL,
    trade_date DATE NOT NULL,
    open_price DECIMAL(18,4),
    high_price DECIMAL(18,4),
    low_price DECIMAL(18,4),
    close_price DECIMAL(18,4) NOT NULL,
    volume BIGINT,
    change_pct DECIMAL(8,4),
    data_source VARCHAR(50),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (company_id) REFERENCES TBL_COMPANY(company_id),
    UNIQUE (company_id, trade_date, data_source)
);

-- Financial Statements (Quarterly/Annual)
CREATE TABLE TBL_FINANCIAL (
    financial_id BIGINT AUTOINCREMENT PRIMARY KEY,
    company_id INTEGER NOT NULL,
    quarter VARCHAR(20) NOT NULL,
    fiscal_year INTEGER,
    fiscal_quarter INTEGER,
    total_revenue DECIMAL(20,2),
    gross_profit DECIMAL(20,2),
    net_income DECIMAL(20,2),
    eps DECIMAL(18,4),
    operating_expense DECIMAL(20,2),
    total_assets DECIMAL(20,2),
    total_liabilities DECIMAL(20,2),
    free_cash_flow DECIMAL(20,2),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (company_id) REFERENCES TBL_COMPANY(company_id),
    UNIQUE (company_id, quarter)
);

-- Market Statistics (Real-time snapshots)
CREATE TABLE TBL_MARKET_STAT (
    stat_id BIGINT AUTOINCREMENT PRIMARY KEY,
    company_id INTEGER NOT NULL,
    snapshot_datetime TIMESTAMP_NTZ NOT NULL,
    price DECIMAL(18,4),
    change_pct DECIMAL(8,4),
    volume BIGINT,
    relative_volume DECIMAL(10,2),
    market_cap DECIMAL(20,2),
    pe_ratio DECIMAL(10,4),
    eps_ttm DECIMAL(18,4),
    eps_growth_yoy DECIMAL(8,4),
    div_yield_pct DECIMAL(8,4),
    sector VARCHAR(100),
    analyst_rating VARCHAR(50),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (company_id) REFERENCES TBL_COMPANY(company_id)
);

-- ============================================================================
-- STAGING SCHEMA - Raw data landing tables
-- ============================================================================
USE SCHEMA STAGING;

-- Stage for TVH historical data
CREATE TABLE STG_TVH_PRICES (
    symbol VARCHAR(20),
    trade_date VARCHAR(50),
    open_price VARCHAR(20),
    high_price VARCHAR(20),
    low_price VARCHAR(20),
    close_price VARCHAR(20),
    change VARCHAR(50),
    volume VARCHAR(20),
    last_day VARCHAR(50),
    loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Stage for EGX30 historical data  
CREATE TABLE STG_EGX30_PRICES (
    trade_date VARCHAR(50),
    price VARCHAR(20),
    open_price VARCHAR(20),
    high_price VARCHAR(20),
    low_price VARCHAR(20),
    volume VARCHAR(20),
    change_pct VARCHAR(20),
    symbol VARCHAR(20),
    loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Stage for financial data
CREATE TABLE STG_FINANCIALS (
    symbol VARCHAR(20),
    row_num VARCHAR(10),
    quarter VARCHAR(20),
    total_revenue VARCHAR(30),
    gross_profit VARCHAR(30),
    net_income VARCHAR(30),
    eps VARCHAR(20),
    operating_expense VARCHAR(30),
    total_assets VARCHAR(30),
    total_liabilities VARCHAR(30),
    free_cash_flow VARCHAR(30),
    loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Stage for real-time market data
CREATE TABLE STG_REALTIME_MARKET (
    symbol VARCHAR(20),
    price VARCHAR(20),
    change_pct VARCHAR(20),
    volume VARCHAR(30),
    rel_volume VARCHAR(20),
    market_cap VARCHAR(30),
    pe_ratio VARCHAR(20),
    eps_ttm VARCHAR(20),
    eps_growth VARCHAR(20),
    div_yield VARCHAR(20),
    sector VARCHAR(100),
    analyst_rating VARCHAR(50),
    snapshot_datetime TIMESTAMP_NTZ,
    loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ============================================================================
-- CREATE INDEXES
-- ============================================================================
USE SCHEMA OPERATIONAL;

CREATE INDEX idx_company_symbol ON TBL_COMPANY(symbol);
CREATE INDEX idx_company_sector ON TBL_COMPANY(sector);
CREATE INDEX idx_price_company_date ON TBL_STOCK_PRICE(company_id, trade_date);
CREATE INDEX idx_price_date ON TBL_STOCK_PRICE(trade_date);
CREATE INDEX idx_financial_company ON TBL_FINANCIAL(company_id);
CREATE INDEX idx_market_stat_company ON TBL_MARKET_STAT(company_id);
CREATE INDEX idx_index_membership_idx ON TBL_INDEX_MEMBERSHIP(index_id);
CREATE INDEX idx_index_membership_company ON TBL_INDEX_MEMBERSHIP(company_id);

-- ============================================================================
-- INSERT REFERENCE DATA
-- ============================================================================

INSERT INTO TBL_INDEX (index_code, index_name, description, is_active) VALUES
    ('EGX30', 'EGX 30 Index', 'Top 30 most liquid and active stocks', TRUE),
    ('EGX70', 'EGX 70 EWI', 'Equally Weighted Index of 70 stocks', TRUE),
    ('EGX100', 'EGX 100', 'Top 100 stocks by liquidity', TRUE);

SELECT 'Database created successfully' AS status;
