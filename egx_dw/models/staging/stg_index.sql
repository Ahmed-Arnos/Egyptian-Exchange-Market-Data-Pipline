{{ config(materialized='table') }}

SELECT
    INDEX_ID,
    TRIM(INDEX_CODE) AS INDEX_CODE,
    TRIM(INDEX_NAME) AS INDEX_NAME,
    TRIM(DESCRIPTION) AS DESCRIPTION,
    IS_ACTIVE
FROM {{ source('operational', 'TBL_INDEX') }}