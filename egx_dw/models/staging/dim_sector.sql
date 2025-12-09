WITH source AS (
    SELECT DISTINCT SECTOR
    FROM {{ ref('stg_companies_fixed') }}
    WHERE SECTOR IS NOT NULL
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['SECTOR']) }} AS sector_id,
    SECTOR AS sector
FROM source