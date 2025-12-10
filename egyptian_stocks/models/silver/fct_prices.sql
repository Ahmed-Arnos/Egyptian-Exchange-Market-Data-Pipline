{{ config(
    materialized='table',
    schema='GOLD'
) }}

SELECT
    symbol,
    date,
    open,
    high,
    low,
    close,
    change_pct,
    volume,
    {{ dbt_utils.generate_surrogate_key(['symbol','date']) }} AS price_id,
    file_name,
    load_ts
FROM {{ ref('stg_prices') }}
WHERE date IS NOT NULL