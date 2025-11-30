Egyptian Exchange Market Data Pipeline
=====================================

A graduation project to build an end‑to‑end data platform for EGX (Egyptian Exchange) market analytics. The pipeline ingests batch data (Kaggle) and real-time market data (via egxpy), streams through Kafka to S3, transforms to Silver using Spark/dbt, and serves analytics in a Gold layer on Snowflake for dashboards.

## Team Members
Ahmed Elsaba (@ahmadelsap3), Karim Yasser, Alaa Hamam, Ahmed Arnos, Eslam Shatto

## Quick Start

### Real-time Streaming Pipeline (Grafana Dashboard) ⭐ NEW

```bash
# One-command setup
./setup_streaming.sh

# Or manually:
# 1. Start all services
cd infrastructure/docker && docker compose -f docker-compose.dev.yml up -d

# 2. Activate venv and install dependencies
source .venv/bin/activate
pip install -r requirements.txt

# 3. Start real-time consumer (Kafka → InfluxDB)
python extract/realtime/consumer_influxdb.py --topic egx_market_data --bootstrap localhost:9093 &

# 4. Start producer (EGX API → Kafka)
python extract/egxpy_streaming/producer_kafka.py \
  --symbols COMI,ETEL --interval Daily --n-bars 10 --poll-interval 60 \
  --bootstrap-servers localhost:9093

# 5. View Grafana dashboard: http://localhost:3000 (admin/admin)
```

### Batch Pipeline (S3 Storage)

```bash
# Start consumer (Kafka → S3)
python extract/streaming/consumer_kafka.py \
  --topic egx_market_data --bucket egx-data-bucket --use-aws

# View data in MinIO: http://localhost:9001 (minioadmin/minioadmin)
```

See `extract/realtime/README.md` for streaming details and `extract/streaming/README.md` for batch pipeline.

Architecture overview
---------------------

### Two Parallel Pipelines

#### 1. Real-time Streaming (NEW ✅)
```
EGX API → Kafka → InfluxDB → Grafana
(egxpy)          (real-time)  (live dashboard)
```
- **Purpose**: Live monitoring, current prices, trading alerts
- **Tools**: Kafka, InfluxDB, Grafana
- **Auto-refresh**: Every 5 seconds
- **Access**: http://localhost:3000

#### 2. Batch Processing (Existing ✅)
```
Sources → Kafka → S3 → Spark/dbt → Snowflake → Power BI
├─ EGX API (historical)
├─ Kaggle datasets
└─ Web scraping
```
- **Purpose**: Historical analysis, reports, ML models
- **Storage**: S3 (streaming/, batch/ folders)
- **Transform**: dbt (recommended) or Spark
- **Warehouse**: Snowflake

**Note**: Both pipelines share the same Kafka topic (`egx_market_data`). Two consumers run in parallel:
- `consumer_influxdb.py` → InfluxDB (real-time)
- `consumer_kafka.py` → S3 (batch storage)

Branching model
---------------

- main: production (release‑ready). Protected branch.
- dev-test: integration branch for collaborative development and testing. All feature branches merge here via PRs.

Typical flow
------------

1. Create a feature branch from `dev-test`: `feature/<scope>-<short-title>`
2. Open a PR to `dev-test`; require 2 approvals and green checks.
3. Merge to `dev-test`; smoke test via Airflow/docker locally.
4. Promote to `main` via a release PR.

## Repository Structure

```
extract/
  realtime/              # ⭐ Real-time streaming pipeline (NEW)
    consumer_influxdb.py # Kafka → InfluxDB for live dashboards
    README.md            # Real-time setup guide
  egxpy_streaming/       # EGX data producer
    producer_kafka.py    # Fetch EGX data → Kafka
  streaming/             # Batch pipeline (S3 storage)
    consumer_kafka.py    # Kafka → S3 for historical analysis
    README.md            # Batch pipeline guide
  kaggle/                # Batch datasets (planned)
  aws/                   # AWS connectivity helpers

infrastructure/
  docker/
    docker-compose.dev.yml  # All services (Kafka, InfluxDB, Grafana, MinIO)
    grafana/                # Grafana dashboards + datasources

setup_streaming.sh     # ⭐ One-command setup for teammates
```
    consumer_kafka.py    # Kafka → S3/MinIO with partitioning
    producer.py          # (Legacy: simulator, kept for testing)
  kaggle/                # Batch extractors (planned)
  aws/                   # AWS connectivity helpers
docs/
  STREAMING_ARCHITECTURE.md  # Detailed streaming pipeline docs
  UPLOAD_TO_S3.md           # Teammate S3 upload guide
  PROJECT_PLAN.md           # Team plan and milestones
  CONTRIBUTION_WORKFLOW.md  # Git workflow and PR checklist
iam/
  create_team_users.sh      # Helper to create IAM users
  egx_team_upload_policy.json
docker-compose.dev.yml      # Local dev stack (Kafka + MinIO)
```

Getting started
---------------

1. Copy `.env.example` to `.env` and set required secrets (if needed).
2. Read `docs/PROJECT_PLAN.md` and `docs/CONTRIBUTION_WORKFLOW.md` to align on tasks.
3. For streaming work, see `docs/STREAMING_ARCHITECTURE.md` and `extract/streaming/README.md`.
4. For AWS S3 uploads, see `docs/UPLOAD_TO_S3.md` (IAM users created for team).

Docs
----

- `docs/PROJECT_PLAN.md` – timeline, milestones, and shared work plan for five teammates.
- `docs/CONTRIBUTION_WORKFLOW.md` – branching, PR, commit conventions, and review checklist.
- `docs/ARCHITECTURE.md` – layers and data model at a glance.
- `docs/STREAMING_ARCHITECTURE.md` – integrated streaming pipeline architecture and message formats.
- `docs/UPLOAD_TO_S3.md` – IAM setup and S3 upload guide for teammates.

Credits and reference
---------------------

We'll use ideas and structure inspired by `@Deathslayer89/DTC_dataEngg/files/Stock-market-analytics` as a reference implementation.

---
*Last Updated: 2025-11-24*
