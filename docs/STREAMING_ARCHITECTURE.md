# Streaming Architecture

## Pipeline

```
EGX API → Kafka Producer → Kafka Topic → [Consumer 1: InfluxDB (real-time)
                                           Consumer 2: S3 (batch)]
```

## Components

### Producer: `extract/egxpy_streaming/producer_kafka.py`
- Fetches OHLCV data via egxpy library
- Publishes to Kafka topic `egx_market_data`
- Partition key: symbol (ensures ordering per symbol)
- Supports polling mode for continuous updates

**Message Format (Daily/Weekly/Monthly):**
```json
{
  "symbol": "COMI",
  "exchange": "EGX",
  "interval": "Daily",
  "datetime": "2025-01-20T00:00:00",
  "open": 45.50, "high": 46.20, "low": 45.10, "close": 46.00,
  "volume": 1250000,
  "ingestion_timestamp": "2025-01-20T14:30:52.123456"
}
```

**Message Format (Intraday):**
```json
{
  "symbol": "COMI",
  "interval": "5 Minute",
  "datetime": "2025-01-20T09:35:00",
  "value": 45.75,
  "field": "close",
  "ingestion_timestamp": "2025-01-20T14:30:52.123456"
}
```

### Kafka Broker
- Topic: `egx_market_data`
- Partitioning: By symbol
- Retention: 7 days (configurable)
- Two parallel consumers: real-time (InfluxDB) + batch (S3)

### Consumer 1: `extract/realtime/consumer_influxdb.py`
- Kafka → InfluxDB time-series database
- Purpose: Live dashboards (Grafana)
- Latency: <5 seconds
- Auto-refresh: 5s interval

### Consumer 2: `extract/streaming/consumer_kafka.py`
- Kafka → S3/MinIO
- Purpose: Historical analysis, dbt transformations
- Supports AWS S3 (production) and MinIO (local)
- Auto-creates buckets if missing

**S3 Key Structure:**
```
streaming/
  date=2025-01-20/
    symbol=COMI/
      143052123456.json
      143052456789.json
    symbol=ETEL/
      143053001234.json
```

Benefits: Partition pruning, efficient date/symbol queries, Spark/Athena compatible

## Usage

**Start services:**
```bash
docker compose -f infrastructure/docker/docker-compose.dev.yml up -d
```

**Run producer:**
```bash
python extract/egxpy_streaming/producer_kafka.py \
  --symbols COMI,ETEL --interval Daily --n-bars 10 --poll-interval 60
```

**Run real-time consumer:**
```bash
python extract/realtime/consumer_influxdb.py \
  --topic egx_market_data --bootstrap localhost:9093
```

**Run batch consumer (local):**
```bash
python extract/streaming/consumer_kafka.py \
  --topic egx_market_data --bucket egx-data-bucket --minio-endpoint http://localhost:9000
```

**Run batch consumer (AWS):**
```bash
export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_REGION=us-east-1
python extract/streaming/consumer_kafka.py \
  --topic egx_market_data --bucket egx-data-bucket --use-aws
```

## Verification

**MinIO Console:** http://localhost:9001 (minioadmin/minioadmin)
**Grafana Dashboard:** http://localhost:3000 (admin/admin)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker | `localhost:9092` |
| `AWS_ACCESS_KEY_ID` | S3/MinIO key | `minioadmin` |
| `AWS_SECRET_ACCESS_KEY` | S3/MinIO secret | `minioadmin` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `MINIO_ENDPOINT` | MinIO URL | `http://localhost:9000` |

---
*Updated: December 2025*
