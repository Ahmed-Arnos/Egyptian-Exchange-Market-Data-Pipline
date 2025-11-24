# Streaming Pipeline - EGX Market Data

## Overview

This is the **integrated streaming pipeline** that fetches real Egyptian Exchange (EGX) data and streams it through Kafka to S3/MinIO storage.

**Pipeline Flow**:
```
EGX API → egxpy producer → Kafka → consumer → S3/MinIO (partitioned by date+symbol)
```

For detailed architecture and message formats, see: `docs/STREAMING_ARCHITECTURE.md`

## Quick Start (Local Dev)

### 1. Install Dependencies

```bash
cd "/home/ahmed-elsaba/Git Repos/Egyptian-Exchange-Market-Data-Pipline"
source .venv/bin/activate
pip install kafka-python boto3  # Already in requirements.txt
```

### 2. Start Infrastructure

```bash
docker-compose -f docker-compose.dev.yml up -d
```

Wait 10-15 seconds for Kafka and MinIO to be ready.

### 3. Run EGXpy Producer (Terminal 1)

Fetch real EGX data and publish to Kafka:

```bash
python extract/egxpy_streaming/producer_kafka.py \
  --symbols COMI,ETEL \
  --interval Daily \
  --n-bars 10 \
  --poll-interval 60
```

This will:
- Fetch daily OHLCV data for COMI and ETEL
- Publish each bar to Kafka topic `egx_market_data`
- Re-fetch every 60 seconds (continuous mode)

### 4. Run Kafka Consumer (Terminal 2)

Consume from Kafka and write to MinIO:

```bash
python extract/streaming/consumer_kafka.py \
  --topic egx_market_data \
  --bucket egx-data-bucket \
  --minio-endpoint http://localhost:9000
```

This will:
- Read messages from Kafka
- Write to MinIO with partitioned keys: `streaming/date=YYYY-MM-DD/symbol=XXX/*.json`
- Create bucket automatically if missing

### 5. Verify Data

**MinIO Console**: http://localhost:9001  
**Login**: `minioadmin` / `minioadmin`  
**Navigate to**: `egx-data-bucket/streaming/`

**Kafka UI**: http://localhost:8080  
**View**: Topics → `egx_market_data` → Messages

You should see folders like:
```
streaming/
  date=2025-11-24/
    symbol=COMI/
      143052123456.json
    symbol=ETEL/
      143053001234.json
```

## Production (AWS S3)

### Configure Credentials

Use the IAM credentials created earlier (see `TEAM_CREDENTIALS.txt`):

```bash
export AWS_ACCESS_KEY_ID=AKIAZB7...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1
```

### Run Consumer with AWS S3

```bash
python extract/streaming/consumer_kafka.py \
  --topic egx_market_data \
  --bucket egx-data-bucket \
  --use-aws
```

### Verify Upload

```bash
aws s3 ls s3://egx-data-bucket/streaming/ --recursive
```

## Legacy PoC Files

### `producer.py` (Simulator - Deprecated)

This was a simple Kafka producer that **simulated** tick messages. It's replaced by the real EGXpy producer (`producer_kafka.py`) but kept for reference.

If you want to test Kafka connectivity without hitting the EGX API:

```bash
python extract/streaming/producer.py --topic egx_ticks --count 100 --interval 0.5 --symbol COMI
```

## Configuration

### Producer Options

```bash
python extract/egxpy_streaming/producer_kafka.py --help
```

Key arguments:
- `--symbols`: Comma-separated symbols (e.g., `COMI,ETEL,HELI`)
- `--interval`: `Daily`, `Weekly`, `Monthly`, or `1 Minute`, `5 Minute`, `30 Minute`
- `--n-bars`: Number of historical bars to fetch (default: 10)
- `--poll-interval`: Re-fetch every N seconds (omit for single run)
- `--topic`: Kafka topic name (default: `egx_market_data`)
- `--bootstrap-servers`: Kafka brokers (default: `localhost:9092`)

### Consumer Options

```bash
python extract/streaming/consumer_kafka.py --help
```

Key arguments:
- `--topic`: Kafka topic (default: `egx_market_data`)
- `--bucket`: S3/MinIO bucket (default: `egx-data-bucket`)
- `--prefix`: S3 key prefix (default: `streaming/`)
- `--use-aws`: Use AWS S3 instead of MinIO
- `--minio-endpoint`: MinIO URL (default: `http://localhost:9000`)
- `--consumer-group`: Kafka consumer group (default: `egx-s3-writer`)

## Troubleshooting

### Kafka connection refused

```bash
# Check Kafka is running
docker ps | grep kafka

# Check logs
docker logs egyptian-exchange-market-data-pipline-kafka-1
```

### MinIO 403 Forbidden

```bash
# Verify credentials
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY

# For local MinIO, use defaults:
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
```

### No data in bucket

```bash
# Check producer is running and publishing
# Look for log messages: "Published N messages for SYMBOL"

# Check consumer is consuming
# Look for log messages: "Wrote streaming/date=.../symbol=.../..."

# Check Kafka topic has messages
docker exec -it egyptian-exchange-market-data-pipline-kafka-1 \
  kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic egx_market_data --from-beginning --max-messages 5
```

## Next Steps

1. **Monitoring**: Add Kafka consumer lag monitoring and alerting
2. **Error Handling**: Implement retry logic and dead-letter queue
3. **Schema**: Add Avro schemas for type safety
4. **Spark**: Create Spark job to read from S3 and write Parquet to silver layer
5. **dbt**: Build models on top of Parquet files

See `docs/STREAMING_ARCHITECTURE.md` for detailed architecture and roadmap.
