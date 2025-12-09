# Egyptian Exchange Market Data Pipeline Architecture

## Overview

Complete end-to-end data pipeline for Egyptian Exchange (EGX) market data, combining batch processing, real-time streaming, and analytics transformations.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          DATA SOURCES                                           │
├──────────────────────────┬──────────────────────────────────────────────────────┤
│   Batch (Historical)     │          Streaming (Real-time)                       │
│   - S3 Bucket            │          - EGX API (egxpy)                          │
│   - CSV Files            │          - 249 companies                             │
│   - EGX30/70/100 lists   │          - 5-minute polling                          │
└──────────┬───────────────┴──────────────────┬───────────────────────────────────┘
           │                                   │
           │                                   │
┌──────────▼───────────────┐       ┌──────────▼──────────────────────────────────┐
│   BATCH INGESTION        │       │   STREAMING INGESTION                       │
│   Python Scripts         │       │   ┌──────────────────┐                      │
│   - Load from S3         │       │   │  Kafka Producer  │                      │
│   - Validate & Transform │       │   │  (producer_kafka)│                      │
│   - Write to Snowflake   │       │   └────────┬─────────┘                      │
└──────────┬───────────────┘       │            │ JSON messages                  │
           │                        │   ┌────────▼─────────┐                      │
           │                        │   │   Kafka Broker   │                      │
           │                        │   │   (port 9093)    │                      │
           │                        │   └────────┬─────────┘                      │
           │                        │            │                                 │
           │                        │   ┌────────▼──────────┐                     │
           │                        │   │  Kafka Consumer   │                     │
           │                        │   │(consumer_snowflake)                     │
           │                        │   └────────┬──────────┘                     │
           │                        │            │ Batch inserts (100 records)    │
           │                        └────────────┼─────────────────────────────────┘
           │                                     │
           └─────────────────────────────────────┼─────────────────────────────────┐
                                                 │                                 │
                                    ┌────────────▼──────────────────────────────┐ │
                                    │   OPERATIONAL DATABASE (Snowflake)        │ │
                                    │   Schema: EGX_OPERATIONAL_DB.OPERATIONAL  │ │
                                    │                                           │ │
                                    │   Tables:                                 │ │
                                    │   - TBL_COMPANY (249 companies)           │ │
                                    │   - TBL_STOCK_PRICE (OHLCV data)         │ │
                                    │   - TBL_FINANCIAL (financial statements)  │ │
                                    │   - TBL_MARKET_STAT (market statistics)   │ │
                                    │   - TBL_INDEX (EGX30/70/100)             │ │
                                    │   - TBL_INDEX_MEMBERSHIP                  │ │
                                    └────────────┬──────────────────────────────┘ │
                                                 │                                 │
                     ┌───────────────────────────┼─────────────────────────────────┘
                     │                           │
                     │                  ┌────────▼──────────────────────────────┐
                     │                  │   DBT TRANSFORMATIONS                 │
                     │                  │   (Orchestrated by Airflow)           │
                     │                  │                                       │
                     │                  │   SILVER LAYER (Staging Models)       │
                     │                  │   - stg_companies                     │
                     │                  │   - stg_stock_prices_unified          │
                     │                  │   - stg_financials                    │
                     │                  │   - stg_market_stats                  │
                     │                  │   - stg_index_membership              │
                     │                  │                                       │
                     │                  │         ↓                             │
                     │                  │                                       │
                     │                  │   GOLD LAYER (Marts)                  │
                     │                  │   - gold_dim_company                  │
                     │                  │   - gold_fct_stock_daily_prices       │
                     │                  │   - gold_fct_index_performance        │
                     │                  │   - vw_* (Analytics views)            │
                     │                  │                                       │
                     │                  └────────┬──────────────────────────────┘
                     │                           │
                     │              ┌────────────▼──────────────────────────────┐
                     │              │   DATA WAREHOUSE (Snowflake)              │
                     │              │   Schemas:                                │
                     │              │   - DWH_SILVER (Staging tables)           │
                     │              │   - DWH_GOLD (Analytics-ready tables)     │
                     │              └────────┬──────────────────────────────────┘
                     │                       │
                     │         ┌─────────────┴──────────────┐
                     │         │                            │
           ┌─────────▼─────────▼────┐          ┌───────────▼──────────────┐
           │   ORCHESTRATION         │          │   VISUALIZATION          │
           │   (Airflow)             │          │   (Grafana / BI Tools)   │
           │                         │          │                          │
           │   DAGs:                 │          │   - Real-time dashboards │
           │   1. dbt_scheduled      │          │   - Performance metrics  │
           │      (twice daily)      │          │   - Market analysis      │
           │   2. egx_full_pipeline  │          │   - Sector comparisons   │
           │      (daily at 1 AM)    │          │                          │
           └─────────────────────────┘          └──────────────────────────┘
```

## Data Flow

### 1. **Batch Processing Flow**
```
S3 Bucket → Python Scripts → Snowflake OPERATIONAL → dbt → DWH_SILVER/GOLD
```
- **Frequency**: On-demand or scheduled
- **Data Volume**: Historical data, bulk loads
- **Processing**: Validation, deduplication, transformation

### 2. **Streaming Processing Flow**
```
EGX API → Kafka Producer → Kafka Topic → Kafka Consumer → Snowflake OPERATIONAL
```
- **Frequency**: Every 5 minutes
- **Companies**: All 249 Egyptian Exchange companies
- **Data**: OHLCV (Open, High, Low, Close, Volume)
- **Batch Size**: 100 records per Snowflake insert

### 3. **Transformation Flow (dbt)**
```
OPERATIONAL Tables → dbt Staging (Silver) → dbt Marts (Gold) → Analytics Views
```
- **Staging**: Data cleaning, type casting, business logic
- **Marts**: Aggregations, calculations, dimensional modeling
- **Tests**: Data quality checks at each layer

## Components

### Infrastructure
- **Docker**: Kafka + Zookeeper containers
- **Airflow**: Workflow orchestration (standalone or Docker)
- **Snowflake**: Cloud data warehouse
- **AWS S3**: Batch data storage

### Applications
- **Producer** (`producer_kafka.py`): Fetches EGX data via egxpy library
- **Consumer** (`consumer_snowflake.py`): Writes Kafka messages to Snowflake
- **dbt Project** (`egx_dw/`): SQL transformations and tests

### Monitoring
- **Health Check Script**: `scripts/monitoring/monitor_streaming.sh`
- **Logs**: `producer.log`, `consumer.log`
- **Airflow UI**: DAG execution monitoring
- **dbt Tests**: Data quality validation

## Airflow DAGs

### 1. `dbt_scheduled_transformations`
**Purpose**: Keep analytics data fresh with regular dbt runs

**Schedule**: Twice daily (2 AM and 2 PM Cairo time)

**Tasks**:
1. Check streaming data health
2. Install dbt dependencies
3. Run staging models
4. Run marts models
5. Run dbt tests
6. Generate documentation

### 2. `egx_full_pipeline`
**Purpose**: Complete end-to-end pipeline orchestration

**Schedule**: Daily at 1 AM Cairo time

**Tasks**:
1. Check streaming pipeline health
2. Check for new batch data in S3
3. Process batch data (if available)
4. Validate data quality
5. Run dbt transformations (staging → marts)
6. Run dbt tests
7. Generate documentation
8. Cleanup old logs

## Data Schemas

### OPERATIONAL Layer (Raw Data)
- **TBL_COMPANY**: Company master data (249 companies)
- **TBL_STOCK_PRICE**: Daily OHLCV price data
- **TBL_FINANCIAL**: Financial statements
- **TBL_MARKET_STAT**: Market statistics
- **TBL_INDEX**: Index definitions (EGX30, EGX70, EGX100)
- **TBL_INDEX_MEMBERSHIP**: Company-index relationships

### SILVER Layer (Staging)
- Clean, validated, unified data
- Business rules applied
- Type conversions completed
- Ready for analytical processing

### GOLD Layer (Marts)
- **Dimensions**: Company, Date, Sector
- **Facts**: Stock prices, Index performance
- **Views**: Pre-aggregated analytics

## Key Metrics

### Pipeline Performance
- **Streaming Latency**: < 5 minutes (poll interval)
- **Batch Insert Size**: 100 records
- **Data Freshness**: Real-time + 5 minutes
- **Companies Coverage**: 249 Egyptian Exchange companies

### Data Quality
- No duplicate company records
- Price data validation (positive values)
- Volume validation (non-negative)
- Recent data checks (< 24 hours)
- dbt test suite (63 tests)

## Operations

### Starting the Pipeline
```bash
# Start streaming (Kafka + Producer + Consumer)
./start_streaming.sh

# Check health
./scripts/monitoring/monitor_streaming.sh

# Start Airflow (if needed)
airflow webserver & airflow scheduler &
```

### Stopping the Pipeline
```bash
# Stop streaming processes
kill <PRODUCER_PID> <CONSUMER_PID>

# Stop Kafka
docker compose -f infrastructure/docker/docker-compose.yml down

# Stop Airflow
pkill -f "airflow webserver"
pkill -f "airflow scheduler"
```

### Manual dbt Runs
```bash
cd egx_dw
source ../.venv-aws/bin/activate
export $(cat .env | grep -v '^#' | xargs)

# Run all models
dbt run

# Run specific layer
dbt run --select staging  # Silver layer
dbt run --select marts    # Gold layer

# Run tests
dbt test

# Generate docs
dbt docs generate
dbt docs serve
```

## Monitoring

### Health Checks
```bash
# Full health check
./scripts/monitoring/monitor_streaming.sh

# Check processes
ps aux | grep -E "(producer|consumer)"

# Check Docker
docker ps

# Check logs
tail -f producer.log
tail -f consumer.log

# Check Snowflake data
SELECT COUNT(*), MAX(CREATED_AT) 
FROM EGX_OPERATIONAL_DB.OPERATIONAL.TBL_STOCK_PRICE 
WHERE DATA_SOURCE = 'STREAMING_API'
AND CREATED_AT > DATEADD(hour, -1, CURRENT_TIMESTAMP());
```

### Airflow Monitoring
- **UI**: http://localhost:8080
- **DAG Status**: Green = Success, Red = Failed
- **Task Logs**: Click on task → View Logs

### Alerts
- Airflow email alerts on DAG failures
- Health check script can be run via cron
- Snowflake query monitoring for data gaps

## Troubleshooting

### Streaming Pipeline Issues
**Symptom**: No new data in Snowflake
**Check**:
1. Producer running? `ps aux | grep producer_kafka`
2. Consumer running? `ps aux | grep consumer_snowflake`
3. Kafka healthy? `docker ps`
4. Check logs: `tail -100 consumer.log`

**Fix**: Restart streaming: `./start_streaming.sh`

### dbt Issues
**Symptom**: dbt tests failing
**Check**:
1. Snowflake credentials valid?
2. Recent data exists in OPERATIONAL tables?
3. Run `dbt debug` to check connection

**Fix**: Review test failures in dbt output

### Airflow Issues
**Symptom**: DAG not running
**Check**:
1. Airflow services running?
2. DAG file syntax correct? `python dag_file.py`
3. Check Airflow logs

**Fix**: Restart Airflow services

## Future Enhancements

1. **Intraday Data**: 5-minute bars for active trading
2. **Machine Learning**: Price prediction models
3. **Alerts**: Price movement notifications
4. **API**: REST API for data access
5. **Advanced Analytics**: Technical indicators, sentiment analysis
6. **Multi-Exchange**: Support for other MENA exchanges

## Reference

Based on architecture patterns from:
- [DTC Data Engineering Project](https://github.com/Deathslayer89/DTC_dataEngg)
- dbt Labs best practices
- Snowflake data warehouse patterns
- Apache Airflow orchestration patterns
