# Data Quality & Null Handling Strategy

## Overview
This dbt project implements comprehensive null handling across Silver (staging) and Gold (marts) layers to ensure data quality and prevent downstream issues.

## Silver Layer (Staging Models)

### stg_companies
**Critical Fields with Null Handling:**
- `symbol`: COALESCE to 'UNKNOWN' (should never be null due to WHERE filter)
- `company_name`: COALESCE to 'Unknown Company'
- `sector`: COALESCE to 'Unclassified'
- `market_cap`: COALESCE to 0
- `analyst_rating`: COALESCE to 'Not Rated'
- `is_active`: COALESCE to TRUE

### stg_stock_prices_unified
**Critical Fields with Null Handling:**
- `open_price`: COALESCE to close_price (if open is null, use close)
- `high_price`: COALESCE to close_price
- `low_price`: COALESCE to close_price
- `volume`: COALESCE to 0
- `change_pct`: COALESCE to 0
- `data_source`: COALESCE to 'UNKNOWN'
- **Required**: trade_date and close_price (filtered out if null)

### stg_financials
**Critical Fields with Null Handling:**
- All financial metrics: COALESCE to 0
  - total_revenue, gross_profit, net_income, eps
  - operating_expense, total_assets, total_liabilities
  - free_cash_flow
- Calculated metrics use COALESCE in formulas (e.g., gross_margin_pct)

## Gold Layer (Marts Models)

### gold_fct_stock_daily_prices
**Additional Null Handling:**
- Re-validates COALESCE on OHLC prices even though staging already handles it
- Ensures volume defaults to 0
- All technical indicators (MA, price changes) handle nulls via LAG/window functions

### gold_dim_company
**Null Handling:**
- Uses COALESCE to merge data from multiple sources (market stats + company table)
- Prioritizes market_stats effective values over company table defaults

## Null Handling Philosophy

1. **Block at Source**: Critical fields (trade_date, close_price, symbol) are filtered with WHERE clauses
2. **Default Values**: Numeric fields default to 0, text fields to meaningful labels
3. **Propagate Intelligence**: Use close_price as fallback for missing OHLC components
4. **Layer Defense**: Apply COALESCE at both Silver and Gold for reliability
5. **Test Everything**: not_null tests on all critical columns

## Testing Strategy

- **not_null tests**: Applied to all business-critical columns
- **unique tests**: Ensure primary keys and unique constraints
- **accepted_values tests**: Validate enums (data_source, trend_signal, etc.)
- **relationships tests**: Verify foreign key integrity (configured as warnings)

