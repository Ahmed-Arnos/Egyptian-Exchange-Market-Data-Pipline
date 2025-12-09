{{ config(materialized='table') }}

WITH base AS (
    SELECT
        PRICE_ID,
        COMPANY_ID,
        TRADE_DATE,
        OPEN_PRICE,
        HIGH_PRICE,
        LOW_PRICE,
        CLOSE_PRICE,
        VOLUME,
        UPPER(TRIM(DATA_SOURCE)) AS DATA_SOURCE,
        CREATED_AT
    FROM {{ source('operational', 'TBL_STOCK_PRICE') }}
),

-- Deduplicate rows by keeping the most recent record for each company + date
dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY COMPANY_ID, TRADE_DATE
            ORDER BY CREATED_AT DESC, PRICE_ID DESC
        ) AS rn
    FROM base
),

final AS (
    SELECT
        PRICE_ID,
        COMPANY_ID,
        TRADE_DATE,
        OPEN_PRICE,
        HIGH_PRICE,
        LOW_PRICE,
        CLOSE_PRICE,
        VOLUME,
        DATA_SOURCE,
        CREATED_AT,
        YEAR(TRADE_DATE) AS TRADE_YEAR,
        MONTH(TRADE_DATE) AS TRADE_MONTH,
        TO_CHAR(TRADE_DATE, 'YYYYMM') AS TRADE_YEARMONTH
    FROM dedup
    WHERE rn = 1   -- keep only the latest row per company/date
)

SELECT *
FROM final
ORDER BY COMPANY_ID, TRADE_DATE
