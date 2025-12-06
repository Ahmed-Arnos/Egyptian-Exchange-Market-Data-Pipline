# Egyptian Exchange Market Data Pipeline

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
infrastructure/docker/   # Kafka, InfluxDB, Grafana, MinIO
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
- MinIO: http://localhost:9001 (minioadmin/minioadmin)
- Kafka UI: http://localhost:8080
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
