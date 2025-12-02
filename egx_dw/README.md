# EGX Data Warehouse - dbt Project

Data transformation layer for the Egyptian Exchange Market Data Pipeline using dbt (data build tool).

## 📁 Project Structure

```
egx_dw/
├── models/
│   ├── staging/          # Raw data from sources (Bronze → Silver)
│   ├── intermediate/     # Cleaned, joined data
│   └── marts/           # Business-ready models (Gold)
│       ├── core/        # Core dimensional models (facts, dimensions)
│       └── finance/     # Financial metrics and analytics
├── macros/              # Reusable SQL functions
├── seeds/               # CSV reference data
├── snapshots/           # Slowly changing dimensions (SCD Type 2)
├── tests/               # Data quality tests
└── dbt_project.yml      # Project configuration
```

## 🏗️ Medallion Architecture

### Bronze → Staging
- Source: InfluxDB, MinIO S3 Bronze bucket
- Models: `stg_*` views
- Purpose: Raw data ingestion, basic validation

### Silver → Intermediate
- Models: `int_*` ephemeral models
- Purpose: Data cleaning, deduplication, standardization

### Gold → Marts
- Models: `dim_*` (dimensions), `fact_*` (facts)
- Purpose: Business-ready dimensional models (Snowflake Schema)

## 🚀 Getting Started

### 1. Configure Profile

Create `~/.dbt/profiles.yml`:

```yaml
egx_dw:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: your_account
      user: your_user
      password: your_password
      role: your_role
      database: egx_dev
      warehouse: compute_wh
      schema: public
      threads: 4
```

### 2. Run Models

```bash
# Run all models
dbt run

# Run specific layer
dbt run --select staging
dbt run --select marts.core

# Test data quality
dbt test
```

## 📊 Planned Models

### Staging
- `stg_stock_prices` - Raw OHLCV data
- `stg_companies` - Company metadata

### Marts - Core (Snowflake Dimensions)
- `dim_date` - Date dimension
- `dim_symbol` - Stock symbols
- `dim_company` - Company details (normalized)
- `dim_sector` - Sector hierarchy
- `dim_exchange` - Exchange information
- `fact_stock_prices` - Daily stock prices

### Marts - Finance
- `fact_daily_performance` - Daily returns & metrics
- `fact_market_indicators` - Market-level aggregations

## 📚 Resources

- [dbt Documentation](https://docs.getdbt.com/)
- [Snowflake dbt Package](https://docs.getdbt.com/reference/warehouse-profiles/snowflake-profile)
