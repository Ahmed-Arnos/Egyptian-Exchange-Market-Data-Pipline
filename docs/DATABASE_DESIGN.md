# Database Design

## Architecture

```
Sources → Operational DB (OLTP) → Data Warehouse (Bronze → Silver → Gold)
```

## Operational Database: `EGX_OPERATIONAL_DB`
Normalized OLTP schema for transaction processing.

### Core Tables

**STOCKS** - Master data
```sql
stock_id, symbol, company_name, sector, market_cap, listed_date, is_active
PK: stock_id | UK: symbol
```

**STOCK_PRICES_DAILY** - Historical prices
```sql
price_id, stock_id, trade_date, open, high, low, close, volume, value_traded, num_trades, source
PK: price_id | UK: (stock_id, trade_date) | FK: stock_id → stocks
Indexes: (stock_id, trade_date), trade_date
```

**STOCK_PRICES_INTRADAY** - Minute-level data
```sql
intraday_id, stock_id, timestamp, price, volume, bid_price, ask_price, source
PK: intraday_id | UK: (stock_id, timestamp) | FK: stock_id → stocks
Index: (stock_id, timestamp)
```

**INDICES** - EGX30, EGX70, EGX100
```sql
index_id, index_code, index_name, description, base_value, base_date, is_active
PK: index_id | UK: index_code
```

**INDEX_CONSTITUENTS** - Stock membership in indices
```sql
constituent_id, index_id, stock_id, weight, effective_date, end_date
PK: constituent_id | UK: (index_id, stock_id, effective_date)
FK: index_id → indices, stock_id → stocks
```

**INDEX_VALUES** - Daily index values
```sql
index_value_id, index_id, trade_date, open, high, low, close, change_pct, volume
PK: index_value_id | UK: (index_id, trade_date) | FK: index_id → indices
```

**CORPORATE_ACTIONS** - Dividends, splits, rights issues
```sql
action_id, stock_id, action_type, announcement_date, ex_date, record_date, payment_date, details
PK: action_id | FK: stock_id → stocks
```

**TRADING_CALENDAR** - Business days, holidays
```sql
calendar_id, trade_date, is_trading_day, is_weekend, is_holiday, holiday_name, market_session
PK: calendar_id | UK: trade_date
```

**DATA_LOAD_LOG** - ETL tracking
```sql
load_id, source_name, load_type, start_time, end_time, records_loaded, records_failed, status, error_message
PK: load_id
```

## Data Warehouse: `EGX_DW`

### Bronze Layer (Raw)
Landing zone for unchanged source data.

```sql
bronze.stock_prices_raw (raw_data VARIANT, source, ingestion_timestamp, file_name, partition_date)
bronze.trading_view_historical_raw (symbol, trade_date, raw_json, loaded_at)
bronze.egxpy_streaming_raw (raw_json, kafka_offset, kafka_partition, ingestion_timestamp)
```

### Silver Layer (Cleaned)
Validated, deduplicated, type-safe data.

**silver.stock_prices_cleaned**
```sql
stock_symbol, trade_date, open, high, low, close, volume, change_pct
is_complete, has_anomaly, source, bronze_id, processed_at
UK: (stock_symbol, trade_date)
```

**silver.index_values_cleaned**
```sql
index_code, trade_date, close_value, change_pct, volume, processed_at
UK: (index_code, trade_date)
```

### Gold Layer (Analytics)

**Dimensions:**

**dim_stock**
```sql
stock_key, stock_symbol, company_name, sector
is_egx30, is_egx70, is_egx100, is_sharia_compliant
effective_date, expiration_date, is_current (SCD Type 2)
PK: stock_key | UK: stock_symbol
```

**dim_date**
```sql
date_key, date_day, year, quarter, month, month_name, week_of_year
day_of_week, day_name, day_of_month, day_of_year
is_trading_day, is_weekend, is_holiday, holiday_name
fiscal_year, fiscal_quarter
PK: date_key
```

**dim_index**
```sql
index_key, index_code, index_name, description, category
PK: index_key | UK: index_code
```

**Facts:**

**fct_stock_daily_prices**
```sql
-- Keys
stock_key, date_key, stock_symbol, trade_date

-- Prices
open, high, low, close, prev_close

-- Volume
volume, value_traded, num_trades

-- Calculations
daily_change, daily_change_pct, daily_range, range_pct

-- Moving Averages
ma_7day, ma_30day, ma_90day, volume_ma_7day

-- Technical Indicators
rsi_14day, trend_signal, volume_signal

UK: (stock_key, date_key)
FK: stock_key → dim_stock, date_key → dim_date
```

**fct_index_daily_values**
```sql
index_key, date_key, open, high, low, close
daily_change, change_pct
total_volume, num_constituents, num_gainers, num_losers, num_unchanged

UK: (index_key, date_key)
FK: index_key → dim_index, date_key → dim_date
```

**fct_corporate_actions**
```sql
action_key, stock_key, announcement_date_key, ex_date_key
action_type, dividend_amount, split_ratio
FK: stock_key → dim_stock, dates → dim_date
```

## Data Flow

1. **Sources → Operational DB**: Real-time inserts, normalized, FK enforced
2. **Operational → Bronze**: CDC/batch, no transformations, audit trail
3. **Bronze → Silver**: Quality checks, deduplication, validation
4. **Silver → Gold**: Dimensional modeling, aggregations, business logic

## Naming Convention

**Operational DB:**
- Tables: `lowercase_with_underscores`
- PKs: `table_name_id`
- FKs: `referenced_table_id`

**Data Warehouse:**
- Bronze: `source_name_raw`
- Silver: `entity_name_cleaned`
- Gold Dims: `dim_entity`
- Gold Facts: `fct_entity_grain`

## Implementation Status

- ✅ dbt models: Bronze → Silver → Gold (13/13 tests passing)
- ✅ S3 integration: Streaming and batch ingestion
- ✅ Snowflake warehouse: 82K+ records, 39 stocks, 2019-2025
- ✅ Grafana dashboards: Real-time + historical analytics
- ⏳ Operational DB: Planned for Phase 2

---
*Generated: December 2025*
