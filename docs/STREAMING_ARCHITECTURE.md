# EGX Data Pipeline Architecture

## Integrated Streaming Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EGYPTIAN EXCHANGE (EGX)                          │
│                     Real-time & Historical Market Data                   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ egxpy library (API calls)
                                 ▼
                    ┌────────────────────────────┐
                    │  EGXpy Kafka Producer      │
                    │  producer_kafka.py         │
                    │                            │
                    │  • Fetches OHLCV data      │
                    │  • Daily/Intraday          │
                    │  • Polling mode support    │
                    └─────────────┬──────────────┘
                                  │
                                  │ Publish messages
                                  │ (symbol as key)
                                  ▼
                    ┌────────────────────────────┐
                    │      Apache Kafka          │
                    │   Topic: egx_market_data   │
                    │                            │
                    │  • Message broker          │
                    │  • Replay capability       │
                    │  • Multiple consumers      │
                    └─────────────┬──────────────┘
                                  │
                                  │ Consume messages
                                  │ (offset tracking)
                                  ▼
                    ┌────────────────────────────┐
                    │   Kafka → S3 Consumer      │
                    │   consumer_kafka.py        │
                    │                            │
                    │  • Reads from Kafka        │
                    │  • Partitions by date+symbol│
                    │  • Atomic writes           │
                    └─────────────┬──────────────┘
                                  │
                                  │ Write JSON objects
                                  │ (date=YYYY-MM-DD/symbol=XXX/*.json)
                                  ▼
                    ┌────────────────────────────┐
                    │    S3 / MinIO Storage      │
                    │    Bucket: egx-data-bucket │
                    │                            │
                    │  streaming/                │
                    │    date=2025-01-20/        │
                    │      symbol=COMI/          │
                    │        143052123456.json   │
                    │      symbol=ETEL/          │
                    │        143052456789.json   │
                    └────────────────────────────┘
```

## Message Flow

### 1. Producer (EGXpy → Kafka)

**Location**: `extract/egxpy_streaming/producer_kafka.py`

**Responsibilities**:
- Fetch data from Egyptian Exchange via `egxpy` library
- Transform DataFrame rows into JSON messages
- Publish to Kafka topic with symbol as partition key
- Support continuous polling for real-time updates

**Message Format** (Daily/Weekly/Monthly):
```json
{
  "symbol": "COMI",
  "exchange": "EGX",
  "interval": "Daily",
  "datetime": "2025-01-20T00:00:00",
  "open": 45.50,
  "high": 46.20,
  "low": 45.10,
  "close": 46.00,
  "volume": 1250000,
  "ingestion_timestamp": "2025-01-20T14:30:52.123456"
}
```

**Message Format** (Intraday):
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

### 2. Kafka Broker

**Topic**: `egx_market_data`  
**Partitioning**: By symbol (ensures all messages for a symbol go to same partition → ordering)  
**Retention**: 7 days (configurable in `docker-compose.dev.yml`)

### 3. Consumer (Kafka → S3)

**Location**: `extract/streaming/consumer_kafka.py`

**Responsibilities**:
- Consume messages from Kafka topic
- Write to S3/MinIO with partitioned keys
- Handle AWS S3 (production) or MinIO (local dev)
- Automatic bucket creation

**S3 Key Structure**:
```
streaming/
  date=2025-01-20/
    symbol=COMI/
      143052123456.json  # timestamp: HHMMSSffffff
      143052456789.json
    symbol=ETEL/
      143053001234.json
  date=2025-01-21/
    symbol=COMI/
      ...
```

**Benefits of this structure**:
- Efficient queries by date range: `s3://bucket/streaming/date=2025-01-2*/`
- Efficient queries by symbol: `s3://bucket/streaming/date=*/symbol=COMI/`
- Compatible with Spark/Athena partition pruning
- Easy backfill and reprocessing

## Local Development Setup

### Prerequisites

```bash
cd "/home/ahmed-elsaba/Git Repos/Egyptian-Exchange-Market-Data-Pipline"
source .venv/bin/activate
pip install kafka-python boto3 egxpy  # Already in requirements.txt
```

### Start Infrastructure

```bash
docker-compose -f docker-compose.dev.yml up -d
```

This starts:
- Zookeeper (port 2181)
- Kafka (port 9092)
- MinIO (port 9000, console: 9001)

### Run Producer (Terminal 1)

```bash
# Continuous polling mode (fetches every 60 seconds)
python extract/egxpy_streaming/producer_kafka.py \
  --symbols COMI,ETEL \
  --interval Daily \
  --n-bars 10 \
  --poll-interval 60 \
  --topic egx_market_data
```

### Run Consumer (Terminal 2)

```bash
# Local MinIO
python extract/streaming/consumer_kafka.py \
  --topic egx_market_data \
  --bucket egx-data-bucket \
  --minio-endpoint http://localhost:9000
```

### Verify Data in MinIO

Open MinIO Console: http://localhost:9001  
Login: `minioadmin` / `minioadmin`  
Browse bucket: `egx-data-bucket/streaming/`

## Production Deployment

### Use AWS S3

```bash
# Set AWS credentials (use teammate IAM users created earlier)
export AWS_ACCESS_KEY_ID=AKIAZB7...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1

# Run consumer with --use-aws flag
python extract/streaming/consumer_kafka.py \
  --topic egx_market_data \
  --bucket egx-data-bucket \
  --use-aws
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker(s) | `localhost:9092` |
| `AWS_ACCESS_KEY_ID` | S3/MinIO access key | `minioadmin` (local) |
| `AWS_SECRET_ACCESS_KEY` | S3/MinIO secret | `minioadmin` (local) |
| `AWS_REGION` | AWS region | `us-east-1` |
| `MINIO_ENDPOINT` | MinIO URL (local dev) | `http://localhost:9000` |

## Next Steps

1. **Monitoring**: Add metrics (messages/sec, lag, errors) using Kafka consumer lag monitoring
2. **Error Handling**: Implement retry logic and dead-letter queue for failed messages
3. **Schema Evolution**: Add Avro or Protobuf schemas for type safety
4. **Spark Integration**: Create Spark Structured Streaming job to read from S3 and write Parquet
5. **Alerting**: Set up CloudWatch/Prometheus alerts for consumer lag and failures

## Legacy Consumer (Deprecated)

The original `extract/egxpy_streaming/consumer.py` wrote directly to disk. It's now replaced by the integrated Kafka pipeline but kept for reference. Consider archiving it.

## Team Responsibilities

- **Ahmed Elsaba, Karim Yasser**: Streaming pipeline (producer + consumer)
- **Alaa Hamam, Ahmed Arnos**: Batch pipeline (Kaggle → S3 → dbt)
- **Eslam Shatto**: Integration (orchestration, warehouse schemas)
