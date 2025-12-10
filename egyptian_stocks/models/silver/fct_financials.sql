{{ config(
    materialized='table',
    schema='GOLD'
) }}

SELECT
    symbol,
    quarter_date,
    total_revenue,
    net_income,
    eps,
    operating_expense,
    total_assets,
    total_liabilities,
    free_cash_flow,
    file_name,
    load_ts,
    {{ dbt_utils.generate_surrogate_key(['symbol','quarter_date']) }} AS financial_id
FROM {{ ref('stg_finance') }}
WHERE quarter_date IS NOT NULL
