{{ config(materialized='table',schema='GOLD') }}

WITH distinct_sectors AS (
    SELECT DISTINCT
        UPPER(TRIM(sector)) AS sector_name
    FROM {{ ref('stg_companies') }}
    WHERE sector IS NOT NULL AND TRIM(sector) <> ''
)

SELECT
    ROW_NUMBER() OVER (ORDER BY sector_name) AS sector_id,
    sector_name
FROM distinct_sectors
ORDER BY sector_name
