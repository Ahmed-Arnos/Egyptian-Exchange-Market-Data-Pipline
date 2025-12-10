{{ config(materialized='view') }}

WITH raw AS (
    SELECT
        raw:"symbol"::string AS symbol,
        TO_DATE(
            '01/' ||
            CASE SPLIT_PART(raw:"quarter"::string, ' ', 1)
                WHEN 'Q1' THEN '01' WHEN 'Q2' THEN '04' WHEN 'Q3' THEN '07' WHEN 'Q4' THEN '10' ELSE NULL
            END || '/20' || REPLACE(SPLIT_PART(raw:"quarter"::string, ' ', 2), '''', ''),
            'DD/MM/YYYY'
        ) AS quarter_date,

        ------------------------------------------------------------------------
        -- 1. Total Revenue
        CASE
        WHEN RIGHT(TRIM(REPLACE(raw:"total_revenue"::string, '∅', '')), 1) = 'T' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_revenue"::string), '∅', ''), 'T', ''), ' ', ''), '−', '-'), 38, 10) * 1000000000000
        WHEN RIGHT(TRIM(REPLACE(raw:"total_revenue"::string, '∅', '')), 1) = 'B' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_revenue"::string), '∅', ''), 'B', ''), ' ', ''), '−', '-'), 38, 10) * 1000000000
        WHEN RIGHT(TRIM(REPLACE(raw:"total_revenue"::string, '∅', '')), 1) = 'M' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_revenue"::string), '∅', ''), 'M', ''), ' ', ''), '−', '-'), 38, 10) * 1000000
        WHEN RIGHT(TRIM(REPLACE(raw:"total_revenue"::string, '∅', '')), 1) = 'K' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_revenue"::string), '∅', ''), 'K', ''), ' ', ''), '−', '-'), 38, 10) * 1000
        ELSE
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_revenue"::string), '∅', ''), ' ', ''), '−', '-'), 38, 10)
        END AS total_revenue,

        ------------------------------------------------------------------------
        -- 2. Net Income
        CASE
        WHEN RIGHT(TRIM(REPLACE(raw:"net_income"::string, '∅', '')), 1) = 'T' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"net_income"::string), '∅', ''), 'T', ''), ' ', ''), '−', '-'), 38, 10) * 1000000000000
        WHEN RIGHT(TRIM(REPLACE(raw:"net_income"::string, '∅', '')), 1) = 'B' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"net_income"::string), '∅', ''), 'B', ''), ' ', ''), '−', '-'), 38, 10) * 1000000000
        WHEN RIGHT(TRIM(REPLACE(raw:"net_income"::string, '∅', '')), 1) = 'M' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"net_income"::string), '∅', ''), 'M', ''), ' ', ''), '−', '-'), 38, 10) * 1000000
        WHEN RIGHT(TRIM(REPLACE(raw:"net_income"::string, '∅', '')), 1) = 'K' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"net_income"::string), '∅', ''), 'K', ''), ' ', ''), '−', '-'), 38, 10) * 1000
        ELSE
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(TRIM(raw:"net_income"::string), '∅', ''), ' ', ''), '−', '-'), 38, 10)
        END AS net_income,

        ------------------------------------------------------------------------
        -- EPS
        REPLACE(REPLACE(raw:"eps"::string, '∅', ''), '−', '-')::float AS eps,

        ------------------------------------------------------------------------
        -- 3. Operating Expense
        CASE
        WHEN RIGHT(TRIM(REPLACE(raw:"operating_expense"::string, '∅', '')), 1) = 'T' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"operating_expense"::string), '∅', ''), 'T', ''), ' ', ''), '−', '-'), 38, 10) * 1000000000000
        WHEN RIGHT(TRIM(REPLACE(raw:"operating_expense"::string, '∅', '')), 1) = 'B' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"operating_expense"::string), '∅', ''), 'B', ''), ' ', ''), '−', '-'), 38, 10) * 1000000000
        WHEN RIGHT(TRIM(REPLACE(raw:"operating_expense"::string, '∅', '')), 1) = 'M' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"operating_expense"::string), '∅', ''), 'M', ''), ' ', ''), '−', '-'), 38, 10) * 1000000
        WHEN RIGHT(TRIM(REPLACE(raw:"operating_expense"::string, '∅', '')), 1) = 'K' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"operating_expense"::string), '∅', ''), 'K', ''), ' ', ''), '−', '-'), 38, 10) * 1000
        ELSE
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(TRIM(raw:"operating_expense"::string), '∅', ''), ' ', ''), '−', '-'), 38, 10)
        END AS operating_expense,

        ------------------------------------------------------------------------
        -- 4. Total Assets
        CASE
        WHEN RIGHT(TRIM(REPLACE(raw:"total_assets"::string, '∅', '')), 1) = 'T' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_assets"::string), '∅', ''), 'T', ''), ' ', ''), '−', '-'), 38, 10) * 1000000000000
        WHEN RIGHT(TRIM(REPLACE(raw:"total_assets"::string, '∅', '')), 1) = 'B' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_assets"::string), '∅', ''), 'B', ''), ' ', ''), '−', '-'), 38, 10) * 1000000000
        WHEN RIGHT(TRIM(REPLACE(raw:"total_assets"::string, '∅', '')), 1) = 'M' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_assets"::string), '∅', ''), 'M', ''), ' ', ''), '−', '-'), 38, 10) * 1000000
        WHEN RIGHT(TRIM(REPLACE(raw:"total_assets"::string, '∅', '')), 1) = 'K' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_assets"::string), '∅', ''), 'K', ''), ' ', ''), '−', '-'), 38, 10) * 1000
        ELSE
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_assets"::string), '∅', ''), ' ', ''), '−', '-'), 38, 10)
        END AS total_assets,

        ------------------------------------------------------------------------
        -- 5. Total Liabilities
        CASE
        WHEN RIGHT(TRIM(REPLACE(raw:"total_liabilities"::string, '∅', '')), 1) = 'T' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_liabilities"::string), '∅', ''), 'T', ''), ' ', ''), '−', '-'), 38, 10) * 1000000000000
        WHEN RIGHT(TRIM(REPLACE(raw:"total_liabilities"::string, '∅', '')), 1) = 'B' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_liabilities"::string), '∅', ''), 'B', ''), ' ', ''), '−', '-'), 38, 10) * 1000000000
        WHEN RIGHT(TRIM(REPLACE(raw:"total_liabilities"::string, '∅', '')), 1) = 'M' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_liabilities"::string), '∅', ''), 'M', ''), ' ', ''), '−', '-'), 38, 10) * 1000000
        WHEN RIGHT(TRIM(REPLACE(raw:"total_liabilities"::string, '∅', '')), 1) = 'K' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_liabilities"::string), '∅', ''), 'K', ''), ' ', ''), '−', '-'), 38, 10) * 1000
        ELSE
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(TRIM(raw:"total_liabilities"::string), '∅', ''), ' ', ''), '−', '-'), 38, 10)
        END AS total_liabilities,

        ------------------------------------------------------------------------
        -- 6. Free Cash Flow
        CASE
        WHEN RIGHT(TRIM(REPLACE(raw:"free_cash_flow"::string, '∅', '')), 1) = 'T' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"free_cash_flow"::string), '∅', ''), 'T', ''), ' ', ''), '−', '-'), 38, 10) * 1000000000000
        WHEN RIGHT(TRIM(REPLACE(raw:"free_cash_flow"::string, '∅', '')), 1) = 'B' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"free_cash_flow"::string), '∅', ''), 'B', ''), ' ', ''), '−', '-'), 38, 10) * 1000000000
        WHEN RIGHT(TRIM(REPLACE(raw:"free_cash_flow"::string, '∅', '')), 1) = 'M' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"free_cash_flow"::string), '∅', ''), 'M', ''), ' ', ''), '−', '-'), 38, 10) * 1000000
        WHEN RIGHT(TRIM(REPLACE(raw:"free_cash_flow"::string, '∅', '')), 1) = 'K' THEN
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(REPLACE(TRIM(raw:"free_cash_flow"::string), '∅', ''), 'K', ''), ' ', ''), '−', '-'), 38, 10) * 1000
        ELSE
            TRY_TO_NUMBER(REPLACE(REPLACE(REPLACE(TRIM(raw:"free_cash_flow"::string), '∅', ''), ' ', ''), '−', '-'), 38, 10)
        END AS free_cash_flow,

        file_name,
        load_ts
    FROM {{ source('bronze', 'FINANCE_RAW') }}
)

SELECT * FROM raw