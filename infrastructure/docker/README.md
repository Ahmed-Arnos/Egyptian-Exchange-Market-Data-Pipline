# Infrastructure Docker Setup

This directory contains the Grafana provisioning configuration.

**Note:** The main docker-compose.dev.yml at the project root now includes all infrastructure services:
- Streaming: Kafka, Zookeeper, InfluxDB, Grafana
- Batch Processing: Airflow, Postgres, Spark, Jupyter
- Storage: MinIO (S3-compatible)
- Monitoring: Kafka-UI

## Usage

From project root:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

The infrastructure/docker/docker-compose.dev.yml file is kept for reference but the main compose file is recommended.
