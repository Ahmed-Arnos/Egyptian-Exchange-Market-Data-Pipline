{{ config(
    materialized='table',
    schema='GOLD'
) }}

WITH cleaned AS (
    SELECT DISTINCT
        -- Clean: trim, uppercase, remove commas/hyphens/periods
        UPPER(
            TRIM(
                REPLACE(
                    REPLACE(
                        REPLACE(headquarters, ',', ' '),
                    '-', ' '),
                '.', ' ')
            )
        ) AS location_name
    FROM {{ ref('stg_companies') }}
    WHERE headquarters IS NOT NULL
      AND TRIM(headquarters) != ''
)

SELECT
    ROW_NUMBER() OVER (ORDER BY location_name) AS location_id,
    location_name
FROM cleaned
