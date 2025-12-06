-- ================================================================
-- EGYPTIAN EXCHANGE OPERATIONAL DATABASE
-- Database: EGX_OPERATIONAL_DB
-- Purpose: Normalized OLTP schema with referential integrity
-- Created: December 5, 2025
-- ================================================================

-- ================================================================
-- SECTION 1: DATABASE AND SCHEMA SETUP
-- ================================================================

-- Create operational database
CREATE DATABASE IF NOT EXISTS EGX_OPERATIONAL_DB
    COMMENT = 'Operational database for Egyptian Exchange market data - OLTP';

USE DATABASE EGX_OPERATIONAL_DB;

-- Create operational schema
CREATE SCHEMA IF NOT EXISTS OPERATIONAL
    COMMENT = 'Main operational schema for normalized transactional data';

USE SCHEMA OPERATIONAL;

-- ================================================================
-- SECTION 2: MASTER DATA TABLES
-- ================================================================

-- Sequences for primary keys
CREATE OR REPLACE SEQUENCE seq_stock_id START = 1 INCREMENT = 1;
CREATE OR REPLACE SEQUENCE seq_index_id START = 1 INCREMENT = 1;
CREATE OR REPLACE SEQUENCE seq_calendar_id START = 1 INCREMENT = 1;
CREATE OR REPLACE SEQUENCE seq_price_id START = 1 INCREMENT = 1;
CREATE OR REPLACE SEQUENCE seq_intraday_id START = 1 INCREMENT = 1;
CREATE OR REPLACE SEQUENCE seq_index_value_id START = 1 INCREMENT = 1;
CREATE OR REPLACE SEQUENCE seq_constituent_id START = 1 INCREMENT = 1;
CREATE OR REPLACE SEQUENCE seq_action_id START = 1 INCREMENT = 1;
CREATE OR REPLACE SEQUENCE seq_load_id START = 1 INCREMENT = 1;

-- Table: STOCKS (Master stock data)
CREATE OR REPLACE TABLE stocks (
    stock_id INTEGER DEFAULT seq_stock_id.NEXTVAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    company_name VARCHAR(200),
    sector VARCHAR(100),
    market_cap DECIMAL(20,2),
    listed_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Master table for stock information';

-- Table: INDICES (Market indices like EGX30, EGX70)
CREATE OR REPLACE TABLE indices (
    index_id INTEGER DEFAULT seq_index_id.NEXTVAL PRIMARY KEY,
    index_code VARCHAR(20) UNIQUE NOT NULL,
    index_name VARCHAR(100),
    description TEXT,
    base_value DECIMAL(10,2),
    base_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Market indices definitions';

-- Table: TRADING_CALENDAR
CREATE OR REPLACE TABLE trading_calendar (
    calendar_id INTEGER DEFAULT seq_calendar_id.NEXTVAL PRIMARY KEY,
    trade_date DATE UNIQUE NOT NULL,
    is_trading_day BOOLEAN DEFAULT TRUE,
    is_weekend BOOLEAN DEFAULT FALSE,
    is_holiday BOOLEAN DEFAULT FALSE,
    holiday_name VARCHAR(100),
    market_session VARCHAR(20) DEFAULT 'FULL'
)
COMMENT = 'Egyptian Exchange trading calendar';

-- ================================================================
-- SECTION 3: TRANSACTIONAL DATA TABLES
-- ================================================================

-- Table: STOCK_PRICES_DAILY (Historical daily prices)
CREATE OR REPLACE TABLE stock_prices_daily (
    price_id BIGINT DEFAULT seq_price_id.NEXTVAL PRIMARY KEY,
    stock_id INTEGER NOT NULL,
    trade_date DATE NOT NULL,
    open_price DECIMAL(18,4),
    high_price DECIMAL(18,4),
    low_price DECIMAL(18,4),
    close_price DECIMAL(18,4) NOT NULL,
    volume BIGINT,
    value_traded DECIMAL(20,2),
    num_trades INTEGER,
    source VARCHAR(50) DEFAULT 'TradingView',
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    CONSTRAINT fk_stock_prices_stock FOREIGN KEY (stock_id) REFERENCES stocks(stock_id),
    CONSTRAINT uk_stock_date UNIQUE (stock_id, trade_date)
)
COMMENT = 'Daily OHLCV stock prices';

-- Table: STOCK_PRICES_INTRADAY (Minute-level data)
CREATE OR REPLACE TABLE stock_prices_intraday (
    intraday_id BIGINT DEFAULT seq_intraday_id.NEXTVAL PRIMARY KEY,
    stock_id INTEGER NOT NULL,
    timestamp TIMESTAMP_NTZ NOT NULL,
    price DECIMAL(18,4) NOT NULL,
    volume INTEGER,
    bid_price DECIMAL(18,4),
    ask_price DECIMAL(18,4),
    source VARCHAR(50) DEFAULT 'egxpy',
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    CONSTRAINT fk_intraday_stock FOREIGN KEY (stock_id) REFERENCES stocks(stock_id),
    CONSTRAINT uk_stock_timestamp UNIQUE (stock_id, timestamp)
)
COMMENT = 'Intraday tick-by-tick price data';

-- Table: INDEX_VALUES (Daily index values)
CREATE OR REPLACE TABLE index_values (
    index_value_id BIGINT DEFAULT seq_index_value_id.NEXTVAL PRIMARY KEY,
    index_id INTEGER NOT NULL,
    trade_date DATE NOT NULL,
    open_value DECIMAL(18,4),
    high_value DECIMAL(18,4),
    low_value DECIMAL(18,4),
    close_value DECIMAL(18,4) NOT NULL,
    change_pct DECIMAL(10,6),
    volume BIGINT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    CONSTRAINT fk_index_values_index FOREIGN KEY (index_id) REFERENCES indices(index_id),
    CONSTRAINT uk_index_date UNIQUE (index_id, trade_date)
)
COMMENT = 'Daily index values for EGX30, EGX70, etc.';

-- ================================================================
-- SECTION 4: RELATIONSHIP TABLES
-- ================================================================

-- Table: INDEX_CONSTITUENTS (Stock membership in indices)
CREATE OR REPLACE TABLE index_constituents (
    constituent_id INTEGER DEFAULT seq_constituent_id.NEXTVAL PRIMARY KEY,
    index_id INTEGER NOT NULL,
    stock_id INTEGER NOT NULL,
    weight DECIMAL(5,4),
    effective_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    CONSTRAINT fk_constituent_index FOREIGN KEY (index_id) REFERENCES indices(index_id),
    CONSTRAINT fk_constituent_stock FOREIGN KEY (stock_id) REFERENCES stocks(stock_id),
    CONSTRAINT uk_index_stock_effective UNIQUE (index_id, stock_id, effective_date)
)
COMMENT = 'Historical index membership and weights';

-- ================================================================
-- SECTION 5: CORPORATE ACTIONS
-- ================================================================

-- Table: CORPORATE_ACTIONS
CREATE OR REPLACE TABLE corporate_actions (
    action_id INTEGER DEFAULT seq_action_id.NEXTVAL PRIMARY KEY,
    stock_id INTEGER NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    announcement_date DATE NOT NULL,
    ex_date DATE,
    record_date DATE,
    payment_date DATE,
    dividend_amount DECIMAL(10,4),
    split_ratio VARCHAR(20),
    details VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    CONSTRAINT fk_action_stock FOREIGN KEY (stock_id) REFERENCES stocks(stock_id)
)
COMMENT = 'Corporate actions (dividends, splits, rights issues)';

-- ================================================================
-- SECTION 6: ETL METADATA
-- ================================================================

-- Table: DATA_LOAD_LOG (ETL tracking)
CREATE OR REPLACE TABLE data_load_log (
    load_id BIGINT DEFAULT seq_load_id.NEXTVAL PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,
    load_type VARCHAR(50) NOT NULL,
    start_time TIMESTAMP_NTZ NOT NULL,
    end_time TIMESTAMP_NTZ,
    records_loaded INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'RUNNING',
    error_message TEXT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'ETL load tracking and audit log';

-- ================================================================
-- SECTION 7: INITIAL SEED DATA
-- ================================================================

-- Insert common indices
INSERT INTO indices (index_code, index_name, description, is_active)
VALUES 
    ('EGX30', 'EGX 30 Index', 'Top 30 companies by liquidity and activity', TRUE),
    ('EGX70', 'EGX 70 Index', 'Next 70 companies after EGX30', TRUE),
    ('EGX100', 'EGX 100 Index', 'Combined EGX30 and EGX70', TRUE),
    ('EGX_SHARIA', 'EGX Sharia Index', 'Sharia-compliant stocks', TRUE),
    ('EGX20_CAPPED', 'EGX 20 Capped Index', 'Top 20 with capped weights', TRUE);

-- Generate trading calendar for 2020-2026
-- (Excluding Egyptian holidays - to be updated with actual holiday dates)
INSERT INTO trading_calendar (trade_date, is_trading_day, is_weekend, is_holiday, market_session)
SELECT 
    DATEADD(day, SEQ4(), '2020-01-01'::DATE) AS trade_date,
    CASE 
        WHEN DAYOFWEEK(DATEADD(day, SEQ4(), '2020-01-01'::DATE)) IN (0, 6) THEN FALSE  -- Sunday=0, Saturday=6
        ELSE TRUE 
    END AS is_trading_day,
    CASE 
        WHEN DAYOFWEEK(DATEADD(day, SEQ4(), '2020-01-01'::DATE)) IN (0, 6) THEN TRUE
        ELSE FALSE 
    END AS is_weekend,
    FALSE AS is_holiday,
    CASE 
        WHEN DAYOFWEEK(DATEADD(day, SEQ4(), '2020-01-01'::DATE)) IN (0, 6) THEN 'CLOSED'
        ELSE 'FULL'
    END AS market_session
FROM TABLE(GENERATOR(ROWCOUNT => 2557))  -- ~7 years of dates
WHERE DATEADD(day, SEQ4(), '2020-01-01'::DATE) <= '2026-12-31';

-- ================================================================
-- SECTION 8: VIEWS FOR CONVENIENCE
-- ================================================================

-- View: Active stocks with current prices
CREATE OR REPLACE VIEW vw_active_stocks_latest AS
SELECT 
    s.stock_id,
    s.symbol,
    s.company_name,
    s.sector,
    spd.trade_date AS last_trade_date,
    spd.close_price AS last_price,
    spd.volume AS last_volume,
    spd.change_pct AS last_change_pct
FROM stocks s
LEFT JOIN (
    SELECT 
        stock_id,
        trade_date,
        close_price,
        volume,
        ((close_price - LAG(close_price) OVER (PARTITION BY stock_id ORDER BY trade_date)) 
         / LAG(close_price) OVER (PARTITION BY stock_id ORDER BY trade_date)) * 100 AS change_pct,
        ROW_NUMBER() OVER (PARTITION BY stock_id ORDER BY trade_date DESC) AS rn
    FROM stock_prices_daily
) spd ON s.stock_id = spd.stock_id AND spd.rn = 1
WHERE s.is_active = TRUE;

-- View: Current index constituents
CREATE OR REPLACE VIEW vw_current_index_constituents AS
SELECT 
    i.index_code,
    i.index_name,
    s.symbol,
    s.company_name,
    ic.weight,
    ic.effective_date
FROM index_constituents ic
JOIN indices i ON ic.index_id = i.index_id
JOIN stocks s ON ic.stock_id = s.stock_id
WHERE ic.end_date IS NULL
ORDER BY i.index_code, ic.weight DESC;

-- View: Trading days only
CREATE OR REPLACE VIEW vw_trading_days AS
SELECT 
    trade_date,
    holiday_name
FROM trading_calendar
WHERE is_trading_day = TRUE
ORDER BY trade_date;

-- ================================================================
-- SECTION 9: GRANT PERMISSIONS (Adjust as needed)
-- ================================================================

-- Grant usage on database and schema
GRANT USAGE ON DATABASE EGX_OPERATIONAL_DB TO ROLE ACCOUNTADMIN;
GRANT USAGE ON SCHEMA OPERATIONAL TO ROLE ACCOUNTADMIN;

-- Grant select/insert/update permissions on all tables
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA OPERATIONAL TO ROLE ACCOUNTADMIN;

-- Grant select on views
GRANT SELECT ON ALL VIEWS IN SCHEMA OPERATIONAL TO ROLE ACCOUNTADMIN;

-- ================================================================
-- VALIDATION QUERIES
-- ================================================================

-- Verify tables were created
SELECT 'Tables created: ' || COUNT(*) AS result
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'OPERATIONAL' AND TABLE_TYPE = 'BASE TABLE';

-- Verify indices were seeded
SELECT 'Indices seeded: ' || COUNT(*) AS result FROM indices;

-- Verify calendar was populated
SELECT 'Calendar days: ' || COUNT(*) AS result FROM trading_calendar;

SELECT 'Operational Database Setup Complete!' AS status;
