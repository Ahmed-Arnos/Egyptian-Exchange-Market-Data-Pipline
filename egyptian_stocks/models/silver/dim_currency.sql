{{ config(
    materialized='table',
    schema='GOLD'
) }}

SELECT
    ROW_NUMBER() OVER (ORDER BY currency_code) AS currency_id,
    currency_code,
    currency_name,
    symbol,
    TRUE AS is_active
FROM (
    SELECT 'EGP' AS currency_code, 'Egyptian Pound' AS currency_name, 'E£' AS symbol
    UNION ALL
    SELECT 'USD', 'US Dollar', '$'
)