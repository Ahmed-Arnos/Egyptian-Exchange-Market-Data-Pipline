# Egyptian Exchange Market Data Pipeline

Complete end-to-end data pipeline for Egyptian Exchange (EGX) market data, combining **batch processing**, **real-time streaming**, and **analytics transformations**.

[![Architecture](https://img.shields.io/badge/Architecture-Kafka%20%2B%20Snowflake%20%2B%20dbt-blue)](docs/ARCHITECTURE.md)
[![Pipeline Status](https://img.shields.io/badge/Pipeline-Operational-green)](#monitoring)

## 🎯 Overview

This project implements a production-ready data pipeline that:
- **Streams** real-time market data for 249 Egyptian Exchange companies
- **Processes** historical batch data from S3
- **Transforms** raw data into analytics-ready tables using dbt
- **Orchestrates** workflows with Airflow
- **Monitors** pipeline health and data quality

## 🏗️ Architecture

```
EGX API → Kafka → Snowflake OPERATIONAL → dbt (Silver/Gold) → Analytics
   ↓                                          ↑
S3 Batch Data ────────────────────────────────┘
```

**Full architecture diagram**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Snowflake account
- AWS account (for S3)

### Installation

1. **Clone repository**
```bash
git clone https://github.com/ahmadelsap3/Egyptian-Exchange-Market-Data-Pipline.git
cd Egyptian-Exchange-Market-Data-Pipline
```

2. **Set up Python environment**
```bash
python -m venv .venv-aws
source .venv-aws/bin/activate
pip install -r requirements.txt
```

3. **Configure credentials**
```bash
# Copy and edit .env file
cp egx_dw/.env.example egx_dw/.env
# Add your Snowflake and AWS credentials
```

4. **Start the pipeline**
```bash
./scripts/start_pipeline.sh
```

That's it! 🎉

## 📊 Components

### 1. Streaming Pipeline (Real-time)
- **Producer**: Fetches live data from EGX API using `egxpy` library
- **Kafka**: Message broker (port 9093)
- **Consumer**: Writes to Snowflake in micro-batches (100 records)
- **Frequency**: Every 5 minutes
- **Coverage**: 249 Egyptian Exchange companies

**Start streaming only**:
```bash
./scripts/start_streaming.sh
```

### 2. Batch Processing (Historical)
- **Source**: CSV files in S3 (`egx-data-bucket`)
- **Processor**: Python script with pandas + Snowflake connector
- **Schedule**: Daily via Airflow (1 AM Cairo time)

**Process batch manually**:
```bash
python extract/batch_processor.py --bucket egx-data-bucket --since 7
```

### 3. dbt Transformations
- **Silver Layer**: Cleaned, validated staging tables
- **Gold Layer**: Analytics-ready dimensional models
- **Tests**: 63 data quality tests

**Run dbt manually**:
```bash
cd egx_dw
source ../.venv-aws/bin/activate
export $(cat .env | grep -v '^#' | xargs)

dbt run          # All models
dbt run --select staging  # Silver only
dbt run --select marts    # Gold only
dbt test         # Data quality tests
dbt docs generate && dbt docs serve  # Documentation
```

### 4. Airflow Orchestration
Two DAGs for workflow automation:

**`dbt_scheduled_transformations`**
- Schedule: Twice daily (2 AM and 2 PM Cairo time)
- Tasks: Run dbt staging → marts → tests → docs

**`egx_full_pipeline`**
- Schedule: Daily at 1 AM Cairo time  
- Tasks: Check health → Process batch → Run dbt → Validate quality

**Access Airflow UI**: http://localhost:8081 (admin/admin)

## 📁 Project Structure

```
Egyptian-Exchange-Market-Data-Pipline/
├── extract/
│   ├── egxpy_streaming/
│   │   └── producer_kafka.py          # Kafka producer
│   ├── streaming/
│   │   └── consumer_snowflake.py      # Kafka consumer → Snowflake
│   └── batch_processor.py             # S3 → Snowflake batch loader
├── egx_dw/                            # dbt project
│   ├── models/
│   │   ├── staging/                   # Silver layer (5 models)
│   │   └── marts/                     # Gold layer (7 models)
│   ├── tests/                         # Data quality tests
│   └── dbt_project.yml
├── airflow/
│   ├── dags/                          # Orchestration DAGs
│   │   ├── dbt_scheduled_transformations.py
│   │   └── egx_full_pipeline.py
│   └── plugins/                       # Custom Airflow plugins
├── infrastructure/
│   └── docker/
│       └── docker-compose.yml         # Kafka, Airflow, Grafana
├── scripts/
│   ├── monitoring/
│   │   └── monitor_streaming.sh       # Health check script
│   └── utils/
└── docs/
    └── ARCHITECTURE.md                # Complete architecture docs
```

## 📈 Data Flow

### Operational Layer (Raw)
**Database**: `EGX_OPERATIONAL_DB.OPERATIONAL`

| Table | Records | Description |
|-------|---------|-------------|
| TBL_COMPANY | 249 | Company master data |
| TBL_STOCK_PRICE | 130K+ | Daily OHLCV price data |
| TBL_FINANCIAL | 3.5K | Financial statements |
| TBL_MARKET_STAT | - | Market statistics |
| TBL_INDEX | 3 | EGX30, EGX70, EGX100 |
| TBL_INDEX_MEMBERSHIP | 176 | Company-index relationships |

### Silver Layer (Staging)
**Schema**: `EGX_OPERATIONAL_DB.DWH_SILVER`
- Cleaned and validated data
- Type conversions applied
- Business rules enforced

### Gold Layer (Analytics)
**Schema**: `EGX_OPERATIONAL_DB.DWH_GOLD`
- `gold_dim_company`: Company dimension
- `gold_fct_stock_daily_prices`: Fact table with prices
- `gold_fct_index_performance`: Index performance metrics
- Plus 4 pre-built analytics views

## 🔍 Monitoring

### Health Check
```bash
./scripts/monitoring/monitor_streaming.sh
```

Checks:
- ✓ Kafka Docker containers running
- ✓ Producer/Consumer processes active
- ✓ Recent data in Snowflake (< 1 hour)
- ✓ Log file sizes
- ⚠ Error rates in logs

### View Logs
```bash
# Real-time monitoring
tail -f logs/producer.log
tail -f logs/consumer.log

# Last 100 lines
tail -100 logs/producer.log
tail -100 logs/consumer.log
```

### Check Data Freshness
```sql
SELECT 
    COUNT(*) as records,
    COUNT(DISTINCT COMPANY_ID) as companies,
    MAX(CREATED_AT) as latest_record
FROM EGX_OPERATIONAL_DB.OPERATIONAL.TBL_STOCK_PRICE
WHERE DATA_SOURCE = 'STREAMING_API'
AND CREATED_AT > DATEADD(hour, -1, CURRENT_TIMESTAMP());
```

### Airflow Monitoring
- **Web UI**: http://localhost:8081
- **DAG Runs**: View execution history
- **Task Logs**: Click task → View Log
- **Email Alerts**: Configured for failures

## 🛠️ Operations

### Start Pipeline
```bash
# Complete pipeline (Kafka + Streaming + Airflow)
./start_pipeline.sh

# Streaming only
./start_streaming.sh
```

### Stop Pipeline
```bash
# Graceful shutdown
./scripts/stop_pipeline.sh

# Or stop specific components
kill <PRODUCER_PID> <CONSUMER_PID>
docker compose -f infrastructure/docker/docker-compose.yml down
```

### Restart Components
```bash
# Restart streaming
./scripts/stop_pipeline.sh
./scripts/start_streaming.sh

# Restart Kafka
docker compose -f infrastructure/docker/docker-compose.yml restart kafka

# Restart Airflow
docker compose -f infrastructure/docker/docker-compose.yml restart airflow airflow-scheduler
```

## 🐛 Troubleshooting

### No New Streaming Data
**Check**:
1. Producer running? `ps aux | grep producer_kafka`
2. Consumer running? `ps aux | grep consumer_snowflake`
3. Kafka healthy? `docker ps | grep kafka`
4. Errors in logs? `tail -100 consumer.log | grep -i error`

**Fix**: `./start_streaming.sh`

### dbt Tests Failing
**Check**:
1. Snowflake connection: `cd egx_dw && dbt debug`
2. Recent data exists in OPERATIONAL tables
3. Review specific test failures in output

**Fix**: 
```bash
cd egx_dw
dbt run --select <failing_model>
dbt test --select <failing_model>
```

### Airflow DAG Not Running
**Check**:
1. Airflow services: `docker ps | grep airflow`
2. DAG syntax: `python infrastructure/airflow/dags/<dag_name>.py`
3. DAG enabled in UI

**Fix**: Check Airflow logs in UI or restart services

## 📊 Dashboards & Visualization

### Grafana
- **URL**: http://localhost:3000
- **Credentials**: admin / admin
- **Data Source**: Snowflake (connect via JDBC)

### Looker Studio / BI Tools
Connect to Snowflake DWH_GOLD schema:
- `gold_dim_company`
- `gold_fct_stock_daily_prices`
- `vw_*` analytics views

## 🔒 Security

- ✅ No hardcoded credentials (all use environment variables)
- ✅ Git history cleaned (sensitive data removed)
- ✅ `.env` files in `.gitignore`
- ✅ Airflow credentials configurable

## 📝 Development

### Running Tests
```bash
# dbt tests
cd egx_dw && dbt test

# Python tests (if added)
pytest tests/
```

### Adding New Models
1. Create SQL file in `egx_dw/models/staging/` or `marts/`
2. Add tests in YAML schema files
3. Run: `dbt run --select <new_model>`
4. Test: `dbt test --select <new_model>`

### Adding New DAG
1. Create Python file in `infrastructure/airflow/dags/`
2. Follow existing DAG patterns
3. Restart Airflow scheduler
4. Enable DAG in UI

## 🎓 Reference & Credits

Architecture inspired by:
- [DTC Data Engineering Project](https://github.com/Deathslayer89/DTC_dataEngg) - Kafka + Spark + dbt patterns
- dbt Labs best practices
- Snowflake data warehouse patterns
- Apache Airflow orchestration patterns

## 📜 License

MIT License - see LICENSE file

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Test changes thoroughly
4. Submit pull request

## 📧 Contact

Ahmed Elsaba - [@ahmadelsap3](https://github.com/ahmadelsap3)

Project Link: https://github.com/ahmadelsap3/Egyptian-Exchange-Market-Data-Pipline

---

**Status**: ✅ Pipeline operational with 249 companies streaming real-time data

Real-time and historical market data platform for EGX (Egyptian Exchange) with streaming ingestion, data warehousing, and analytics dashboards.

## Team
Ahmed Elsaba, Karim Yasser, Alaa Hamam, Ahmed Arnos, Eslam Shatto

## Architecture

**Real-time Path:**
```
EGX API → Kafka → InfluxDB → Grafana (5s refresh)
```

**Batch Path:**
```
Sources → Kafka → S3 → Snowflake (Bronze) → dbt (Silver/Gold) → Grafana
```

Both pipelines consume from the same Kafka topic (`egx_market_data`):
- `consumer_influxdb.py` → real-time dashboard
- `consumer_kafka.py` → S3 historical storage

## Quick Start

### Real-time Dashboard
```bash
# Start services
docker compose -f infrastructure/docker/docker-compose.dev.yml up -d

# Start consumers
source .venv/bin/activate
python extract/realtime/consumer_influxdb.py --topic egx_market_data --bootstrap localhost:9093 &

# Start producer
python extract/egxpy_streaming/producer_kafka.py \
  --symbols COMI,ETEL --interval Daily --n-bars 10 --bootstrap-servers localhost:9093

# Access: http://localhost:3000 (admin/admin)
```

### Historical Analytics (dbt)
```bash
# Setup S3 integration (one-time)
./setup_s3_pipeline.sh

# Run transformations
cd egx_dw && dbt run --profiles-dir ~/.dbt
dbt test --profiles-dir ~/.dbt

# View: Grafana unified dashboard (historical + real-time)
```

## Repository Structure
```
extract/
├── egxpy_streaming/     # EGX API → Kafka producer
├── realtime/            # Kafka → InfluxDB consumer
├── streaming/           # Kafka → S3 consumer
└── kaggle/              # Historical datasets

egx_dw/                  # dbt project
├── models/
│   ├── staging/         # Bronze → Silver (cleaned)
│   └── marts/           # Silver → Gold (analytics)
└── tests/               # Data quality tests

sql/                     # Snowflake setup scripts
infrastructure/docker/   # Kafka, InfluxDB, Grafana
iam/                     # AWS IAM for S3 access
docs/                    # Technical documentation
```

## Data Flow

**Current Metrics:**
- 82K+ records (2019-2025)
- 39 stocks tracked
- 13/13 dbt tests passing
- Real-time latency <5s

## Git Workflow

**Branches:**
- `main`: Production releases (protected)
- `dev-test`: Integration branch
- `feature/<scope>-<description>`: Feature work

**Process:**
1. Branch from `dev-test`
2. PR to `dev-test` (requires 2 approvals)
3. Merge to `dev-test` → smoke test
4. Release PR to `main`

## Documentation

- `egx_dw/README.md` - dbt setup and workflow
- `extract/README.md` - Data extraction pipelines
- `docs/ARCHITECTURE.md` - System design
- `docs/DATABASE_DESIGN.md` - Schema and data model
- `docs/STREAMING_ARCHITECTURE.md` - Streaming pipeline
- `docs/UPLOAD_TO_S3.md` - S3 upload guide
- `docs/CONTRIBUTION_WORKFLOW.md` - Git workflow
- `docs/PROJECT_PLAN.md` - Team milestones

## Local Services

- Grafana: http://localhost:3000 (admin/admin)
- Kafka UI: http://localhost:8082
- InfluxDB: http://localhost:8086 (admin/admin123456)
- Snowflake: See `docs/UPLOAD_TO_S3.md` for credentials

## Tech Stack
- **Streaming**: Kafka, InfluxDB
- **Storage**: AWS S3, Snowflake
- **Transform**: dbt (medallion architecture)
- **Orchestration**: Docker Compose
- **Visualization**: Grafana
- **Languages**: Python, SQL

---
*Pipeline Status: ✅ Operational | Last Updated: December 2025*
