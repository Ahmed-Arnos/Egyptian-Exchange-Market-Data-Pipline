-- Company dimension table with SCD Type 1
{{
    config(
        materialized='table',
        tags=['gold', 'dimension']
    )
}}

WITH company_base AS (
    SELECT 
        company_id,
        symbol,
        company_name,
        sector,
        industry,
        logo_url,
        analyst_rating,
        is_active,
        created_at,
        updated_at
    FROM {{ ref('stg_companies') }}
),

latest_market_stats AS (
    SELECT 
        company_id,
        price as latest_price,
        change_pct as latest_change_pct,
        market_cap,
        pe_ratio,
        eps_ttm,
        div_yield_pct,
        effective_sector,
        analyst_rating as market_analyst_rating,
        snapshot_datetime,
        ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY snapshot_datetime DESC) AS rn
    FROM {{ ref('stg_market_stats') }}
),

latest_stats AS (
    SELECT * FROM latest_market_stats WHERE rn = 1
),

company_prices AS (
    SELECT 
        symbol,
        MAX(trade_date) AS latest_price_date,
        COUNT(DISTINCT trade_date) AS trading_days_available
    FROM {{ ref('stg_stock_prices_unified') }}
    GROUP BY symbol
),

company_dimension AS (
    SELECT 
        -- Primary key
        c.company_id,
        c.symbol,
        
        -- Company info
        c.company_name,
        COALESCE(s.effective_sector, c.sector) as sector,
        c.industry,
        
        -- Market metrics (from TradingView data)
        s.latest_price,
        s.latest_change_pct,
        s.market_cap,
        s.pe_ratio,
        s.eps_ttm,
        s.div_yield_pct,
        COALESCE(s.market_analyst_rating, c.analyst_rating) as analyst_rating,
        
        -- Logo
        c.logo_url,
        
        -- Data availability
        cp.latest_price_date,
        cp.trading_days_available,
        c.is_active,
        
        -- Metadata
        s.snapshot_datetime as latest_market_data_at,
        c.created_at as ingested_at,
        c.updated_at as company_last_updated,
        CURRENT_TIMESTAMP() AS dbt_updated_at
        
    FROM company_base c
    LEFT JOIN company_prices cp ON c.symbol = cp.symbol
    LEFT JOIN latest_stats s ON c.company_id = s.company_id
)

SELECT * FROM company_dimension
