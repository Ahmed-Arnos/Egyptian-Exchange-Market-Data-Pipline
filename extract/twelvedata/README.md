# Twelvedata Streaming Consumer

This directory contains a streaming consumer for the [Twelvedata API](https://twelvedata.com/), which can fetch real-time and historical time-series data for Egyptian Exchange (EGX) stocks.

## Overview

The `stream_consumer.py` script polls the Twelvedata API at configurable intervals and can:
- Fetch 1-minute, 5-minute, or other interval OHLCV bars for Egyptian stocks
- Write events to local JSON files (bronze layer)
- Be extended to produce events to a Kafka topic for downstream streaming consumers

## Requirements

- Python 3.12+
- Twelvedata API key with **Pro plan or higher** (Egyptian stocks require Pro tier)
- Environment variable `TWELVEDATA_API_KEY` or pass `--api-key` flag

## Setup

Install dependencies (already in `requirements.txt`):
```bash
# From repo root
.venv/bin/pip install requests
```

Set your API key:
```bash
export TWELVEDATA_API_KEY=your_api_key_here
```

## Usage

### Single fetch (run once and exit)
```bash
.venv/bin/python extract/twelvedata/stream_consumer.py \
  --symbol EGS01041C010 \
  --interval 1min \
  --outputsize 5
```

### Streaming mode (poll every 60 seconds)
```bash
.venv/bin/python extract/twelvedata/stream_consumer.py \
  --symbol EGS01041C010,EGS02051C018 \
  --interval 1min \
  --poll-interval 60 \
  --outdir extract/twelvedata/raw
```

### Fetch multiple symbols
```bash
.venv/bin/python extract/twelvedata/stream_consumer.py \
  --symbol EGS01041C010,EGS02051C018,EGS02091C014 \
  --interval 5min \
  --outputsize 10 \
  --poll-interval 300
```

## Symbol Format

Egyptian stocks on Twelvedata use ISIN-style symbols (e.g., `EGS01041C010`). You can list all available Egyptian stocks with:

```bash
curl "https://api.twelvedata.com/stocks?country=Egypt&apikey=YOUR_API_KEY" | python -m json.tool
```

Example symbols:
- `EGS01041C010` — Ismailia National Food Industries Co.
- `EGS02051C018` — Cairo Poultry Co.
- `EGS02091C014` — Mansoura Poultry Company

## API Tier Requirements

⚠️ **Important**: Egyptian stock data requires a **Pro plan** on Twelvedata. The free tier returns a 404 error:
```json
{
  "code": 404,
  "message": "This symbol is available starting with Pro (Pro plan). Consider upgrading now at https://twelvedata.com/pricing",
  "status": "error"
}
```

**Pricing**: Check [https://twelvedata.com/pricing](https://twelvedata.com/pricing) for current Pro plan rates.

## Streaming Architecture

The script is designed to be a **polling-based streaming consumer**:
- It fetches new data at regular intervals (configurable via `--poll-interval`)
- Each fetch can return the latest N data points (via `--outputsize`)
- Events can be saved to disk (JSON) or sent to Kafka (extend the script with `kafka-python` or `confluent-kafka`)

### Kafka Integration (Future)

To produce events to Kafka, add this pattern to `stream_consumer.py`:

```python
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# In the fetch loop:
producer.send('egx_ticks', value=data)
producer.flush()
```

Then run a Kafka consumer to write to bronze S3/Parquet or forward to Spark Structured Streaming.

## Alternatives

If the Pro plan is not available, consider:
1. **EGX Web Scraper** (`extract/egx/scraper.py`) — scrapes the EGX website directly (free, but requires hardening for production use)
2. **Kaggle Historical Dataset** (`extract/kaggle/download_kaggle.py`) — batch historical data for backfills
3. **Massive S3 Flatfiles** (`extract/massive/s3_consumer.py`) — if EGX data becomes available in the Massive bucket

## Next Steps

1. Upgrade Twelvedata API key to Pro plan (or use alternative source)
2. Test streaming with valid credentials
3. Add Kafka producer integration (optional)
4. Deploy as a containerized service with Docker
5. Monitor via Airflow DAG or systemd service

## References

- [Twelvedata API Docs](https://twelvedata.com/docs)
- [Twelvedata Pricing](https://twelvedata.com/pricing)
- [Egyptian Exchange (EGX)](https://www.egx.com.eg/)
