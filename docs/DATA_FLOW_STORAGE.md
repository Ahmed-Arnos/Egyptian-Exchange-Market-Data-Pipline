# Data Flow & Storage Guide

## Overview

The EGX streaming pipeline continuously fetches data for 16 companies and stores it in multiple locations for different purposes.

## 16 Companies Tracked

Based on EGX30 most liquid stocks:
```
COMI, ETEL, SWDY, PHDC, ORAS, ESRS, HRHO, OCDI, 
SKPC, TMGH, JUFO, EKHO, CLHO, OTMT, BTFH, HELI
```

## Data Flow Architecture

```
┌─────────────┐
│  EGX API    │ (egxpy library)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Producer  │ extract/egxpy_streaming/producer_kafka.py
└──────┬──────┘
       │
       ↓
┌─────────────┐
│    Kafka    │ Topic: egx_market_data
└──────┬──────┘
       │
       ├─────────────────────┐
       ↓                     ↓
┌──────────────┐     ┌──────────────┐
│ Consumer #1  │     │ Consumer #2  │
│ (Real-time)  │     │   (Batch)    │
└──────┬───────┘     └──────┬───────┘
       │                    │
       ↓                    ↓
┌──────────────┐     ┌──────────────┐
│  InfluxDB    │     │   AWS S3     │
└──────┬───────┘     └──────┬───────┘
       │                    │
       ↓                    ↓
┌──────────────┐     ┌──────────────┐
│   Grafana    │     │  Snowflake   │
│ (Live Views) │     │   + dbt      │
└──────────────┘     └──────┬───────┘
                            │
                            ↓
                     ┌──────────────┐
                     │   Grafana    │
                     │ (Historical) │
                     └──────────────┘
```

## Storage Locations

### 1. Real-time Storage (InfluxDB)
**Path**: InfluxDB container → `market_data` bucket  
**Purpose**: Live dashboard monitoring  
**Retention**: 7-30 days (configurable)  
**Access**: Grafana dashboards at http://localhost:3000  
**Data Format**: Time-series optimized for fast queries

### 2. Historical Storage (AWS S3)
**Path**: `s3://egx-data-bucket/streaming/`  
**Structure**:
```
streaming/
  date=2025-12-06/
    symbol=COMI/
      143052123456.json
      143052789012.json
    symbol=ETEL/
      143053001234.json
  date=2025-12-07/
    ...
```
**Purpose**: 
- Long-term historical data storage
- Source for batch analytics
- Backup and reprocessing

**Data Format**: JSON files, partitioned by date and symbol  
**Access**: AWS S3 Console, or via boto3/aws cli

### 3. Analytics Storage (Snowflake)
**Path**: Snowflake warehouse → `EGX_DW` database  
**Structure**:
```
EGX_DW
├── BRONZE (Raw from S3)
│   └── stock_prices_raw
├── SILVER (Cleaned)
│   └── stock_prices_cleaned
└── GOLD (Analytics)
    ├── dim_stock
    ├── dim_date
    ├── fct_stock_daily_prices
    └── vw_gold_* (Grafana views)
```
**Purpose**: 
- Data warehouse for analytics
- Technical indicators & aggregations
- Historical reporting

**Data Format**: Structured tables with star schema  
**Access**: Snowflake console, dbt, Grafana

## Data Pipeline Components

### Producer (Airflow Managed)
**Script**: `extract/egxpy_streaming/producer_kafka.py`  
**Function**: Fetch data from EGX API every 5 minutes  
**Command**:
```bash
python extract/egxpy_streaming/producer_kafka.py \
  --symbols COMI,ETEL,SWDY,PHDC,ORAS,ESRS,HRHO,OCDI,SKPC,TMGH,JUFO,EKHO,CLHO,OTMT,BTFH,HELI \
  --interval Daily \
  --n-bars 30 \
  --poll-interval 300
```

### Consumer 1: Real-time (Airflow Managed)
**Script**: `extract/realtime/consumer_influxdb.py`  
**Function**: Stream to InfluxDB for live dashboards  
**Command**:
```bash
python extract/realtime/consumer_influxdb.py \
  --topic egx_market_data \
  --bootstrap localhost:9093
```

### Consumer 2: Batch (Airflow Managed)
**Script**: `extract/streaming/consumer_kafka.py`  
**Function**: Store to S3 for historical analysis  
**Command**:
```bash
python extract/streaming/consumer_kafka.py \
  --topic egx_market_data \
  --bucket egx-data-bucket
```

### dbt Transformations (Airflow Managed)
**Location**: `egx_dw/`  
**Function**: S3 → Snowflake → Analytics models  
**Schedule**: Daily at 2 AM

## Airflow DAG Structure

Create `airflow/dags/egx_streaming_pipeline.dag.py`:

```python
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'egx-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 12, 6),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'egx_streaming_pipeline',
    default_args=default_args,
    description='EGX real-time data streaming pipeline',
    schedule_interval='@continuous',  # Always running
    catchup=False,
) as dag:

    # Start producer (long-running)
    producer = BashOperator(
        task_id='kafka_producer',
        bash_command='python extract/egxpy_streaming/producer_kafka.py --symbols COMI,ETEL,SWDY,PHDC,ORAS,ESRS,HRHO,OCDI,SKPC,TMGH,JUFO,EKHO,CLHO,OTMT,BTFH,HELI --interval Daily --n-bars 30 --poll-interval 300',
    )

    # Start consumers (long-running)
    consumer_influx = BashOperator(
        task_id='consumer_influxdb',
        bash_command='python extract/realtime/consumer_influxdb.py --topic egx_market_data --bootstrap localhost:9093',
    )

    consumer_s3 = BashOperator(
        task_id='consumer_s3',
        bash_command='python extract/streaming/consumer_kafka.py --topic egx_market_data --bucket egx-data-bucket',
    )

    [producer] >> [consumer_influx, consumer_s3]
```

Separate DAG for daily transformations:

```python
with DAG(
    'egx_dbt_transformations',
    default_args=default_args,
    description='Daily dbt transformations S3 → Snowflake',
    schedule_interval='0 2 * * *',  # 2 AM daily
    catchup=False,
) as dag:

    dbt_run = BashOperator(
        task_id='dbt_run',
        bash_command='cd egx_dw && dbt run --profiles-dir ~/.dbt',
    )

    dbt_test = BashOperator(
        task_id='dbt_test',
        bash_command='cd egx_dw && dbt test --profiles-dir ~/.dbt',
    )

    dbt_run >> dbt_test
```

## Quick Start

### 1. One-time Setup
```bash
# Setup S3 integration with Snowflake
./scripts/setup_s3_pipeline.sh

# Start Docker services
cd infrastructure/docker && docker compose up -d
```

### 2. Configure Airflow
```bash
# Access Airflow
http://localhost:8081
# Username: admin
# Password: admin

# Enable DAGs:
# - egx_streaming_pipeline
# - egx_dbt_transformations
```

### 3. Monitor
- **Real-time Dashboard**: http://localhost:3000 (Grafana)
- **Airflow UI**: http://localhost:8081
- **Kafka UI**: http://localhost:8082
- **S3 Data**: AWS Console → egx-data-bucket
- **Snowflake**: Snowflake Console → EGX_DW

## Data Retention

| Location | Retention | Purpose |
|----------|-----------|---------|
| InfluxDB | 30 days | Live monitoring |
| S3 | Indefinite | Historical archive |
| Snowflake | Indefinite | Analytics warehouse |

## Troubleshooting

**Producer not fetching data:**
- Check egxpy API limits
- Verify symbols are valid
- Check Kafka connectivity

**Consumers not writing:**
- Verify AWS credentials (S3)
- Check InfluxDB connection
- Verify Kafka topic exists

**dbt transformations failing:**
- Check Snowflake credentials
- Verify S3 data exists
- Run `dbt debug --profiles-dir ~/.dbt`

## For Graduation Discussion

**Data Volume** (estimated for 16 companies):
- Raw data: ~500 records/day (16 companies × ~30 historical bars)
- Storage: ~50 KB/day in S3
- Monthly: ~1.5 MB
- Until graduation (3-6 months): ~5-10 MB

**Monitoring Screenshots to Prepare**:
1. Grafana real-time dashboard showing all 16 stocks
2. S3 bucket structure with partitioned data
3. Snowflake tables with record counts
4. dbt test results (13/13 passing)
5. Airflow DAG execution history

**Key Metrics to Show**:
- Total records processed
- Data quality test results
- Pipeline uptime
- End-to-end latency (API → Grafana)
