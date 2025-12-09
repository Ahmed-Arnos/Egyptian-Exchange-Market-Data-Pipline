{{
  config(
    materialized='incremental',
    unique_key=['company_id', 'quarter']
  )
}}

-- Staging for financial statements with company info
SELECT 
    f.financial_id,
    f.company_id,
    c.symbol,
    c.company_name,
    c.sector,
    f.quarter,
    f.fiscal_year,
    f.fiscal_quarter,
    f.total_revenue,
    f.gross_profit,
    f.net_income,
    f.eps,
    f.operating_expense,
    f.total_assets,
    f.total_liabilities,
    f.free_cash_flow,
    -- Derived metrics
    CASE 
        WHEN f.total_revenue > 0 THEN (f.gross_profit / f.total_revenue) * 100 
        ELSE NULL 
    END as gross_margin_pct,
    CASE 
        WHEN f.total_revenue > 0 THEN (f.net_income / f.total_revenue) * 100 
        ELSE NULL 
    END as net_margin_pct,
    CASE 
        WHEN f.total_assets > 0 THEN (f.net_income / f.total_assets) * 100 
        ELSE NULL 
    END as roa_pct,
    CASE
        WHEN f.total_liabilities > 0 
        THEN f.total_assets / f.total_liabilities
        ELSE NULL
    END as debt_to_asset_ratio,
    f.created_at as ingested_at,
    CURRENT_TIMESTAMP() as updated_at
FROM {{ source('operational', 'TBL_FINANCIAL') }} f
INNER JOIN {{ source('operational', 'TBL_COMPANY') }} c 
    ON f.company_id = c.company_id
WHERE f.quarter IS NOT NULL
{% if is_incremental() %}
  AND f.created_at > (SELECT COALESCE(MAX(ingested_at), '1900-01-01'::timestamp) FROM {{ this }})
{% endif %}
