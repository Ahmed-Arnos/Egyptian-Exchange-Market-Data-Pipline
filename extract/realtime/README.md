# Real-time Streaming Pipeline

This directory contains the **real-time streaming pipeline** for EGX market data visualization.

## Architecture

```
EGX API → Kafka → InfluxDB → Grafana
          (egxpy)              (Live Dashboard)
```

This is **separate** from the batch pipeline (`streaming/consumer_kafka.py → S3`).

## Components

### 1. InfluxDB (Time-Series Database)
- Stores real-time market data optimized for time-series queries
- Automatically handles data retention
- Perfect for OHLCV (Open, High, Low, Close, Volume) data

### 2. Grafana (Visualization)
- Live dashboards with auto-refresh (5 seconds)
- Pre-configured dashboard with:
  - Stock price charts
  - Trading volume
  - OHLC candlestick view
  - Real-time statistics

### 3. Consumer (`consumer_influxdb.py`)
- Consumes from Kafka topic `egx_market_data`
- Writes to InfluxDB in real-time
- Runs alongside the S3 consumer (both read same topic)

## Quick Start

### Step 1: Start Services

```bash
# Start Kafka, Zookeeper, InfluxDB, Grafana
cd infrastructure/docker
docker compose -f docker-compose.dev.yml up -d

# Wait 15 seconds for services to be ready
```

### Step 2: Install Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate

# Install InfluxDB client
pip install influxdb-client
```

### Step 3: Start Real-time Consumer

```bash
# From project root
python extract/realtime/consumer_influxdb.py \
  --topic egx_market_data \
  --bootstrap localhost:9093 \
  --log-level INFO
```

### Step 4: Publish Data

```bash
# In another terminal, run the producer
python extract/egxpy_streaming/producer_kafka.py \
  --symbols COMI,ETEL,HELI,SWDY \
  --interval Daily \
  --n-bars 20 \
  --poll-interval 60 \
  --topic egx_market_data \
  --bootstrap-servers localhost:9093
```

### Step 5: View Dashboard

Open http://localhost:3000 in your browser

- **Username**: `admin`
- **Password**: `admin`
- Dashboard will auto-load: "EGX Market Data - Real-time"

## Services & Ports

| Service | Port | URL | Credentials |
|---------|------|-----|-------------|
| Grafana | 3000 | http://localhost:3000 | admin / admin |
| InfluxDB | 8086 | http://localhost:8086 | admin / admin123456 |
| Kafka | 9093 | localhost:9093 | - |
| Kafka UI | 8080 | http://localhost:8080 | - |

## InfluxDB Configuration

- **Organization**: `egx`
- **Bucket**: `market_data`
- **Token**: `egx-market-data-token-2025`

## Data Structure in InfluxDB

```
Measurement: stock_price
Tags:
  - symbol (COMI, ETEL, etc.)
  - exchange (EGX)
  - interval (Daily, 5 Minute, etc.)
  
Fields:
  - open (float)
  - high (float)
  - low (float)
  - close (float)
  - volume (int)
  
Timestamp: datetime from EGX API
```

## Troubleshooting

### InfluxDB not starting
```bash
# Check logs
docker logs influxdb

# Restart service
docker restart influxdb
```

### Grafana shows "No Data"
1. Check if consumer is running: `ps aux | grep consumer_influxdb`
2. Check if producer is publishing data
3. Verify InfluxDB has data:
   ```bash
   # Access InfluxDB UI
   open http://localhost:8086
   # Login: admin / admin123456
   # Query: from(bucket: "market_data") |> range(start: -1h)
   ```

### Consumer connection errors
```bash
# Check Kafka is running
docker ps | grep kafka

# Test Kafka connection
docker exec -it docker-kafka-1 kafka-topics --list --bootstrap-server localhost:9093
```

## Production Deployment

For production, update environment variables:

```bash
export INFLUXDB_URL=https://your-influxdb-cloud.com
export INFLUXDB_TOKEN=your-production-token
export INFLUXDB_ORG=your-org
export INFLUXDB_BUCKET=production_market_data

python extract/realtime/consumer_influxdb.py \
  --influxdb-url $INFLUXDB_URL \
  --influxdb-token $INFLUXDB_TOKEN \
  --bootstrap your-kafka-cluster:9092
```

## Parallel Pipelines

Both pipelines run simultaneously:

1. **Real-time (this directory)**:
   - Kafka → InfluxDB → Grafana
   - For: Live monitoring, alerts, current prices

2. **Batch** (`extract/streaming/`):
   - Kafka → S3 → Spark/dbt → Snowflake → Power BI
   - For: Historical analysis, reports, ML models

Both consumers read from the **same Kafka topic** (`egx_market_data`).
