-- ================================================================
-- SEED DATA FOR OPERATIONAL DATABASE
-- ================================================================

USE DATABASE EGX_OPERATIONAL_DB;
USE SCHEMA OPERATIONAL;

-- Insert common indices
INSERT INTO indices (index_code, index_name, description, is_active)
VALUES 
    ('EGX30', 'EGX 30 Index', 'Top 30 companies by liquidity and activity', TRUE),
    ('EGX70', 'EGX 70 Index', 'Next 70 companies after EGX30', TRUE),
    ('EGX100', 'EGX 100 Index', 'Combined EGX30 and EGX70', TRUE),
    ('EGX_SHARIA', 'EGX Sharia Index', 'Sharia-compliant stocks', TRUE),
    ('EGX20_CAPPED', 'EGX 20 Capped Index', 'Top 20 with capped weights', TRUE);

-- Generate trading calendar for 2020-2026
INSERT INTO trading_calendar (trade_date, is_trading_day, is_weekend, is_holiday, market_session)
SELECT 
    DATEADD(day, SEQ4(), '2020-01-01'::DATE) AS trade_date,
    CASE 
        WHEN DAYOFWEEK(DATEADD(day, SEQ4(), '2020-01-01'::DATE)) IN (0, 6) THEN FALSE
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
FROM TABLE(GENERATOR(ROWCOUNT => 2557))
WHERE DATEADD(day, SEQ4(), '2020-01-01'::DATE) <= '2026-12-31';

-- Verify seed data
SELECT 'Indices seeded: ' || COUNT(*) AS result FROM indices;
SELECT 'Calendar days: ' || COUNT(*) AS result FROM trading_calendar;
SELECT 'Trading days: ' || COUNT(*) AS result FROM trading_calendar WHERE is_trading_day = TRUE;
