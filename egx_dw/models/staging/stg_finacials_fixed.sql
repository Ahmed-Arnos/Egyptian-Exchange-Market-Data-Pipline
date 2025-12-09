{{ config(materialized='table') }}

WITH base AS (
    SELECT
        COMPANY_ID,

        -- Basic cleaning
        UPPER(TRIM(SYMBOL)) AS SYMBOL,
        TRIM(QUARTER) AS RAW_QUARTER,

        -- Derivative fields
        REGEXP_SUBSTR(QUARTER, 'Q[1-4]') AS FISCAL_QUARTER,

        2000 + TRY_TO_NUMBER(
            REPLACE(
                REGEXP_SUBSTR(QUARTER, '''[0-9]{2}'), 
                '''',
                ''
            )
        ) AS FISCAL_YEAR,

        -- No numeric conversion, just cleaning & whitespace removal
        TRIM(TOTAL_REVENUE) AS TOTAL_REVENUE,
        TRIM(GROSS_PROFIT) AS GROSS_PROFIT,
        TRIM(NET_INCOME) AS NET_INCOME,
        TRIM(EPS) AS EPS,
        TRIM(OPERATING_EXPENSE) AS OPERATING_EXPENSE,
        TRIM(TOTAL_ASSETS) AS TOTAL_ASSETS,
        TRIM(TOTAL_LIABILITIES) AS TOTAL_LIABILITIES,
        TRIM(FREE_CASH_FLOW) AS FREE_CASH_FLOW

    FROM {{ source('operational', 'TBL_FINANCIAL_RAW') }}
)

SELECT *
FROM base
