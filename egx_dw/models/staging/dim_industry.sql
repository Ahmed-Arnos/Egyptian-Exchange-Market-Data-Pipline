{{ config(materialized='table') }}

WITH source AS (
    SELECT DISTINCT INDUSTRY
    FROM {{ ref('stg_companies_fixed') }}
    WHERE INDUSTRY IS NOT NULL
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['INDUSTRY']) }} AS industry_id,
    INDUSTRY AS industry
FROM source