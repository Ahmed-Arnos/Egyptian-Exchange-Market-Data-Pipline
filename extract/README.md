# Data Extraction

Ingestion pipelines for EGX market data from multiple sources.

## Components

### Real-time Streaming
**Location**: `realtime/`
- `consumer_influxdb.py` - Kafka → InfluxDB for live dashboards
- Latency: <5 seconds
- Output: InfluxDB time-series for Grafana

### Batch Streaming
**Location**: `streaming/`
- `consumer_kafka.py` - Kafka → S3 for historical analysis
- Output: Partitioned Parquet files in S3

### EGX Producer
**Location**: `egxpy_streaming/`
- `producer_kafka.py` - EGX API → Kafka topic `egx_market_data`
- Uses egxpy library for market data
- Configurable polling interval

### Historical Data
**Location**: `kaggle/`
- `download_kaggle.py` - Kaggle datasets (2019-2025)
- Dataset: `saurabhshahane/egyptian-stock-exchange`

## Usage

**Real-time pipeline:**
```bash
# Start consumer
python extract/realtime/consumer_influxdb.py --topic egx_market_data --bootstrap localhost:9093 &

# Start producer
python extract/egxpy_streaming/producer_kafka.py \
  --symbols COMI,ETEL --interval Daily --n-bars 10
```

**Batch pipeline:**
```bash
python extract/streaming/consumer_kafka.py \
  --topic egx_market_data --bucket egx-data-bucket --use-aws
```

**Kaggle historical:**
```bash
python extract/kaggle/download_kaggle.py \
  --dataset saurabhshahane/egyptian-stock-exchange \
  --outdir extract/kaggle/raw
```

## Data Flow

```
EGX API → Kafka → [InfluxDB (real-time) + S3 (batch)] → Snowflake → Grafana
```

Both consumers run in parallel on the same Kafka topic.

