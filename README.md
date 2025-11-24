Egyptian Exchange Market Data Pipeline
=====================================

A graduation project to build an end‑to‑end data platform for EGX (Egyptian Exchange) market analytics. The pipeline ingests batch data (Kaggle) and real-time market data (via egxpy), streams through Kafka to S3, transforms to Silver using Spark/dbt, and serves analytics in a Gold layer on Snowflake for dashboards.

## Team Members
Ahmed Elsaba (@ahmadelsap3), Karim Yasser, Alaa Hamam, Ahmed Arnos, Eslam Shatto

## Quick Start

### Local Streaming Pipeline

```bash
# 1. Activate venv
source .venv/bin/activate

# 2. Start Kafka + MinIO
docker-compose -f docker-compose.dev.yml up -d

# 3. Run producer (fetch EGX data → Kafka)
python extract/egxpy_streaming/producer_kafka.py \
  --symbols COMI,ETEL --interval Daily --n-bars 10 --poll-interval 60

# 4. Run consumer (Kafka → S3/MinIO)
python extract/streaming/consumer_kafka.py \
  --topic egx_market_data --bucket egx-data-bucket

# 5. View data in MinIO: http://localhost:9001 (minioadmin/minioadmin)
```

See `extract/streaming/README.md` for detailed setup and `docs/STREAMING_ARCHITECTURE.md` for architecture.

Architecture overview
---------------------

### Integrated Streaming Pipeline (Implemented ✅)
```
EGX API → egxpy producer → Kafka → consumer → S3/MinIO
  ↓                          ↓                    ↓
Daily/Intraday OHLCV    Topic: egx_market_data   Partitioned: date=*/symbol=*/*.json
```

### Full Pipeline (Planned)

- **Extract**: 
  - Streaming: EGX data via `egxpy` → Kafka → S3 (✅ implemented)
  - Batch: Kaggle datasets → S3 Bronze (planned)
- **Load (Bronze)**: Raw data in S3 with date/symbol partitioning
- **Transform (Silver)**:
  - Streaming: Spark Structured Streaming from S3 → Parquet
  - Batch: dbt transformations for curated models
- **Serve (Gold)**: Snowflake as the data warehouse for BI
- **Orchestrate**: Apache Airflow
- **Containerize**: Docker

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
  egxpy_streaming/       # EGX data fetcher + Kafka producer
    producer_kafka.py    # Fetch EGX data → publish to Kafka
    consumer.py          # (Legacy: direct-to-disk, deprecated)
  streaming/             # Kafka consumer
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
