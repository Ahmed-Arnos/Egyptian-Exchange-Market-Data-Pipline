Streaming PoC (local dev)

This folder contains simple producer/consumer examples to run a local E2E streaming proof-of-concept using `docker-compose.dev.yml`.

Requirements
- Docker & Docker Compose
- Python 3.12 virtualenv (`.venv`) with project requirements

Install Python deps (in repo root):

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install kafka-python boto3
```

Start local infra

```bash
docker-compose -f docker-compose.dev.yml up -d
# wait a few seconds for services to be healthy
```

Create bucket in MinIO console (`http://localhost:9001`) or using AWS CLI configured to use MinIO endpoint.

Run consumer (writes to MinIO):

```bash
.venv/bin/python extract/streaming/consumer_kafka.py --topic egx_ticks --bucket egx-bucket
```

Run producer (simulate ticks):

```bash
.venv/bin/python extract/streaming/producer.py --topic egx_ticks --count 100 --interval 0.5 --symbol COMI
```

Notes
- The producer and consumer use `kafka-python` and `boto3`. Install them in the venv.
- MinIO default credentials in `docker-compose.dev.yml`: `minioadmin` / `minioadmin`.
- This PoC is intentionally minimal; for production use add error handling, retries, batching, and metrics.
