# dbt Data Warehouse

Transformation layer implementing medallion architecture (Bronze → Silver → Gold) for EGX market data.

## Structure

```
models/
├── staging/          # Bronze → Silver (cleaned data)
├── intermediate/     # Silver transformations (not used yet)
└── marts/            # Silver → Gold (analytics-ready)
    ├── core/         # Dimensional models
    └── finance/      # Business metrics

macros/               # Reusable SQL functions
tests/                # Data quality tests
```

## Architecture

**Bronze (S3)** → **Silver (staging models)** → **Gold (marts)**

- Bronze: Raw JSON from Kafka → S3
- Silver: Type-safe, deduplicated, validated
- Gold: Dimensional models (facts/dims) for analytics

## Setup

**profiles.yml** (~/.dbt/):
```yaml
egx_dw:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: <account>
      user: <user>
      password: <password>
      role: <role>
      database: egx_dev
      warehouse: compute_wh
      schema: public
      threads: 4
```

## Usage

```bash
# Run all transformations
dbt run --profiles-dir ~/.dbt

# Run specific layer
dbt run --select staging          # Silver layer
dbt run --select marts.core       # Gold layer

# Test data quality
dbt test --profiles-dir ~/.dbt    # 13/13 tests passing

# Generate documentation
dbt docs generate --profiles-dir ~/.dbt
dbt docs serve --profiles-dir ~/.dbt
```

## Models

**Staging (Silver):**
- `stg_stock_prices` - Cleaned OHLCV data
- `stg_companies` - Company metadata

**Marts (Gold):**
- `dim_date` - Date dimension
- `dim_symbol` - Stock dimension
- `dim_company` - Company dimension
- `dim_sector` - Sector hierarchy
- `dim_exchange` - Exchange info
- `fact_stock_prices` - Daily prices (82K+ rows)
- `fact_daily_performance` - Returns & metrics
- `fact_market_indicators` - Market aggregations

## Current Status

- ✅ 82,322 records processed (2019-2025)
- ✅ 39 stocks tracked
- ✅ 13/13 data quality tests passing
- ✅ Grafana integration complete

## Resources

- [dbt Docs](https://docs.getdbt.com/)
- [Snowflake Profile](https://docs.getdbt.com/reference/warehouse-profiles/snowflake-profile)

