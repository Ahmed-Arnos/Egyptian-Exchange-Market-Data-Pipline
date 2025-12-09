{{ config(materialized='table') }}

SELECT
    COMPANY_ID,

    COALESCE(SYMBOL, 'Unknown')            AS SYMBOL,
    COALESCE(COMPANY_NAME, 'Unknown')      AS COMPANY_NAME,
    COALESCE(CURRENCY, 'Unknown')          AS CURRENCY,
    COALESCE(SECTOR, 'Unknown')            AS SECTOR,
    COALESCE(INDUSTRY, 'Unknown')          AS INDUSTRY,
    COALESCE(CEO_NAME, 'Unknown')          AS CEO_NAME,
    COALESCE(WEBSITE, 'Unknown')           AS WEBSITE,
    COALESCE(HEADQUARTERS, 'Unknown')      AS HEADQUARTERS,
    COALESCE(FOUNDED_DATE,'unknown')       as FOUNDED_DATE
    COALESCE(ISIN, 'Unknown')              AS ISIN,
    COALESCE(LOGO_URL, 'Unknown')          AS LOGO_URL,

    COALESCE(IS_ACTIVE, FALSE)             AS IS_ACTIVE,   -- Optional: default boolean

    CREATED_AT,
    UPDATED_AT

FROM {{ source('operational', 'TBL_COMPANY') }}

