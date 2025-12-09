# Egyptian Exchange Pipeline - Project Structure

Complete directory structure and file organization.

## Root Directory

```
Egyptian-Exchange-Market-Data-Pipline/
├── airflow/                           # Airflow DAGs and configuration
├── docs/                              # Documentation
├── egx_dw/                            # dbt project for data warehouse
├── extract/                           # Data ingestion scripts
├── iam/                               # AWS IAM and security setup
├── infrastructure/                    # Docker and service configuration
├── scripts/                           # Utility and automation scripts
├── sql/                               # Database schemas and setup
├── README.md                          # Main documentation
├── requirements.txt                   # Python dependencies
└── Makefile                           # Build automation
```

## Detailed Structure

### 📁 airflow/
Airflow orchestration for workflow automation.

```
airflow/
├── dags/
│   ├── dbt_scheduled_transformations.py   # Twice daily dbt runs (2 AM & 2 PM)
│   ├── egx_full_pipeline.py              # Complete daily pipeline (1 AM)
│   └── egx_unified_pipeline.py.old       # Legacy DAG (disabled)
├── logs/                                  # Airflow execution logs
└── plugins/                               # Custom Airflow plugins
```

**Active DAGs:**
- `dbt_scheduled_transformations`: Runs dbt staging → marts → tests → docs
- `egx_full_pipeline`: Batch processing + dbt + data validation

### 📁 docs/
Documentation and architecture diagrams.

```
docs/
├── database/
│   └── DATABASE_REBUILD_SUMMARY.md        # Database rebuild documentation
├── dbt/
│   ├── DBT_COMPLETION_REPORT.md           # dbt implementation report
│   └── DBT_MODEL_UPDATE_SUMMARY.md        # Model changes documentation
├── ARCHITECTURE.md                        # Complete architecture guide ⭐
├── ARCHITECTURE_DIAGRAM.md                # Visual diagrams
├── CLEANUP_SUMMARY.md                     # Git cleanup documentation
├── EGX_INDICES.md                         # Egyptian Exchange indices info
├── PROJECT_STRUCTURE.md                   # This file
└── UPLOAD_TO_S3.md                        # S3 upload guide
```

### 📁 egx_dw/
dbt project for data transformations (Silver → Gold layers).

```
egx_dw/
├── models/
│   ├── staging/                           # Silver layer (5 models)
│   │   ├── stg_companies.sql
│   │   ├── stg_stock_prices_unified.sql
│   │   ├── stg_financials.sql
│   │   ├── stg_market_stats.sql
│   │   ├── stg_index_membership.sql
│   │   └── schema.yml                     # Tests and documentation
│   ├── marts/                             # Gold layer (7 models)
│   │   ├── gold_dim_company.sql           # Company dimension
│   │   ├── gold_fct_stock_daily_prices.sql # Price fact table
│   │   ├── gold_fct_index_performance.sql  # Index performance
│   │   ├── vw_company_performance_summary.sql
│   │   ├── vw_market_overview.sql
│   │   ├── vw_sector_analysis.sql
│   │   ├── vw_top_gainers_losers.sql
│   │   └── schema.yml
│   └── intermediate/                      # Temporary transformations
├── macros/
│   ├── get_custom_schema.sql              # Schema naming logic
│   └── cleanup_old_schemas.sql            # Maintenance macro
├── tests/                                 # Custom data quality tests
├── dbt_project.yml                        # dbt configuration
├── profiles.yml                           # Snowflake connection
└── packages.yml                           # dbt dependencies
```

**Key Commands:**
```bash
dbt run            # Run all transformations
dbt test           # Run all tests (63 tests)
dbt docs generate  # Generate documentation
```

### 📁 extract/
Data ingestion scripts for batch and streaming.

```
extract/
├── aws/
│   └── connect_aws.py                     # AWS S3 connection utilities
├── egxpy_streaming/
│   └── producer_kafka.py                  # Kafka producer (EGX API → Kafka)
├── streaming/
│   ├── consumer_snowflake.py              # Kafka consumer (Kafka → Snowflake)
│   ├── consumer_kafka.py                  # Alternative consumer
│   └── producer.py                        # Alternative producer
├── eodhd_api/                             # EODHD API integration (unused)
├── kaggle/                                # Kaggle dataset downloads
├── realtime/
│   └── consumer_influxdb.py               # InfluxDB consumer (metrics)
└── batch_processor.py                     # S3 CSV → Snowflake loader ⭐
```

**Main Scripts:**
- `egxpy_streaming/producer_kafka.py`: Fetches EGX data every 5 minutes
- `streaming/consumer_snowflake.py`: Writes to Snowflake in batches (100 records)
- `batch_processor.py`: Loads historical CSV files from S3

### 📁 iam/
AWS IAM setup and security policies.

```
iam/
├── bootstrap_admin.py                     # Initial admin user setup
├── create_bucket.sh                       # S3 bucket creation
├── create_team_users.sh                   # Team user provisioning
├── setup_aws_iam.sh                       # Complete IAM setup
├── egx_team_upload_policy.json            # S3 upload permissions
├── snowflake-s3-read-policy.json          # Snowflake S3 integration
└── snowflake-trust-policy.json            # Cross-account trust
```

### 📁 infrastructure/
Service orchestration and Docker configuration.

```
infrastructure/
└── docker/
    ├── grafana/                           # Grafana configuration
    ├── docker-compose.yml                 # All services (Kafka, Airflow, Grafana) ⭐
    ├── Dockerfile                         # Custom Airflow image
    ├── requirements.txt                   # Docker Python dependencies
    ├── setup.sh                           # Initial Docker setup
    └── start_services.sh                  # Start all Docker services
```

**Services in docker-compose.yml:**
- Zookeeper (Kafka coordination)
- Kafka (port 9093)
- Airflow webserver (port 8081)
- Airflow scheduler
- Airflow init
- InfluxDB (metrics storage)
- Grafana (visualization, port 3000)

### 📁 scripts/
Utility scripts for data loading and monitoring.

```
scripts/
├── loaders/
│   ├── load_all_data_batch.py             # Batch load all data types
│   ├── load_index_membership.py           # EGX30/70/100 membership
│   └── load_market_stats.py               # Market statistics
├── monitoring/
│   └── monitor_streaming.sh               # Pipeline health check ⭐
├── utils/
│   └── check_s3_bucket.py                 # S3 bucket validation
├── bootstrap.sh                           # Initial project setup
└── setup_s3_pipeline.sh                   # S3 pipeline configuration
```

**Key Script:**
- `monitoring/monitor_streaming.sh`: Health checks for Kafka, processes, Snowflake data

### 📁 sql/
Database schemas and setup scripts.

```
sql/
└── 00_create_database_from_scratch.sql    # Complete Snowflake schema setup
```

Creates:
- `EGX_OPERATIONAL_DB` database
- `OPERATIONAL` schema (6 tables)
- `DWH_SILVER` schema (staging)
- `DWH_GOLD` schema (analytics)

## Root Files

### Automation Scripts

| File | Purpose | Usage |
|------|---------|-------|
| `scripts/start_pipeline.sh` | Master startup (Kafka → Streaming → Airflow) | `./scripts/start_pipeline.sh` |
| `scripts/start_streaming.sh` | Streaming only | `./scripts/start_streaming.sh` |
| `scripts/stop_pipeline.sh` | Graceful shutdown | `./scripts/stop_pipeline.sh` |

### Configuration Files

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies (egxpy, kafka, snowflake, dbt) |
| `Makefile` | Build automation targets |
| `.env.example` | Environment variable template |
| `.gitignore` | Git exclusions |

### Log Files

| File | Generated By |
|------|--------------|
| `producer.log` | Kafka producer (EGX data fetching) |
| `consumer.log` | Kafka consumer (Snowflake writes) |

## Data Schemas

### Operational Layer
**Database:** `EGX_OPERATIONAL_DB.OPERATIONAL`

| Table | Records | Source | Description |
|-------|---------|--------|-------------|
| TBL_COMPANY | 249 | Batch + Streaming | Company master data |
| TBL_STOCK_PRICE | 130K+ | Batch + Streaming | OHLCV daily prices |
| TBL_FINANCIAL | 3.5K | Batch | Financial statements |
| TBL_MARKET_STAT | - | Batch | Market statistics |
| TBL_INDEX | 3 | Batch | EGX30, EGX70, EGX100 |
| TBL_INDEX_MEMBERSHIP | 176 | Batch | Company-index relationships |

### Silver Layer (Staging)
**Schema:** `EGX_OPERATIONAL_DB.DWH_SILVER`
- Cleaned, validated, type-converted data
- 5 staging models

### Gold Layer (Analytics)
**Schema:** `EGX_OPERATIONAL_DB.DWH_GOLD`
- Analytics-ready dimensional models
- 3 fact/dimension tables + 4 views

## File Naming Conventions

### Python Scripts
- `producer_*.py` - Data producers (fetch from APIs)
- `consumer_*.py` - Data consumers (write to databases)
- `load_*.py` - Batch loading scripts
- `check_*.py` - Validation utilities

### SQL Files
- `stg_*.sql` - Staging models (Silver layer)
- `gold_*.sql` - Analytics models (Gold layer)
- `vw_*.sql` - Views for analytics
- `00_*.sql` - Setup scripts (ordered)

### Shell Scripts
- `start_*.sh` - Startup scripts
- `stop_*.sh` - Shutdown scripts
- `setup_*.sh` - Configuration scripts
- `monitor_*.sh` - Health check scripts

## Key Paths for Configuration

### Environment Variables
```bash
# Main environment file
egx_dw/.env

# Variables needed:
SNOWFLAKE_ACCOUNT=...
SNOWFLAKE_USER=...
SNOWFLAKE_PASSWORD=...
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=EGX_OPERATIONAL_DB
SNOWFLAKE_ROLE=SYSADMIN
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

### Docker Volumes
```yaml
# Airflow DAGs mount
../../airflow/dags:/opt/airflow/dags

# Logs mount
../../airflow/logs:/opt/airflow/logs
```

### dbt Profiles
```yaml
# Location: egx_dw/profiles.yml
egx_dw:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      # ... other Snowflake configs
```

## Navigation Guide

### To Work On...

**Streaming Pipeline:**
```bash
cd extract/egxpy_streaming/        # Producer
cd extract/streaming/              # Consumer
./start_streaming.sh               # Start both
```

**dbt Transformations:**
```bash
cd egx_dw
source ../.venv-aws/bin/activate
dbt run
```

**Airflow DAGs:**
```bash
cd airflow/dags/
# Edit dbt_scheduled_transformations.py or egx_full_pipeline.py
docker compose -f infrastructure/docker/docker-compose.yml restart airflow-scheduler
```

**Monitoring:**
```bash
./scripts/monitoring/monitor_streaming.sh
tail -f producer.log consumer.log
```

**Documentation:**
```bash
cd docs/
# Edit ARCHITECTURE.md or other docs
```

## Quick Reference

### Start Everything
```bash
./scripts/start_pipeline.sh
```

### Stop Everything
```bash
./scripts/stop_pipeline.sh
```

### Check Health
```bash
./scripts/monitoring/monitor_streaming.sh
```

### View Logs
```bash
tail -f producer.log consumer.log
```

### Airflow UI
http://localhost:8081 (admin/admin)

### Grafana
http://localhost:3000 (admin/admin)

---

**Last Updated:** December 9, 2025  
**Total Files:** 100+  
**Total Lines of Code:** ~15,000+
