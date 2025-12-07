# Infrastructure Docker Setup

Complete data engineering infrastructure for EGX Market Data Pipeline.

## ⚠️ IMPORTANT: Configuration Required

**Before starting services**, you MUST configure AWS credentials:

1. Edit `infrastructure/docker/.env`
2. Add your AWS credentials:
```bash
AWS_ACCESS_KEY_ID=AKIA...your-key...
AWS_SECRET_ACCESS_KEY=your-secret-key-here
```

## Quick Start

```bash
cd infrastructure/docker

# Option 1: Use setup script
./start_services.sh

# Option 2: Manual start
docker compose up -d
```

**Access URLs:**
- Airflow: http://localhost:8081 (admin/admin)
- Grafana: http://localhost:3000 (admin/admin)
- Kafka UI: http://localhost:8082

## Services Included

### 📊 Real-time Streaming
- **Kafka** (9093) - Message broker
- **Zookeeper** (2181) - Kafka coordination
- **InfluxDB** (8086) - Time-series database
- **Grafana** (3000) - Dashboards and visualization
- **Kafka-UI** (8082) - Kafka monitoring

### 🔧 Orchestration
- **Airflow** (8081) - Workflow orchestration
- **Postgres** (5432) - Airflow metadata store

## Usage


## Usage

### Start All Services
```bash
cd infrastructure/docker
docker compose up -d
```

### Check Service Status
```bash
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f airflow
```

### Access Services
- Airflow: http://localhost:8081 (admin/admin)
- Grafana: http://localhost:3000 (admin/admin)
- Kafka-UI: http://localhost:8082
- InfluxDB: http://localhost:8086

### Stop Services
```bash
docker compose down
```

### Clean Volumes (⚠️ Deletes all data)
```bash
docker compose down -v
```

## Configuration

### Environment Variables (.env)
```bash
# PostgreSQL (Airflow metadata)
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow

# AWS Credentials (Required)
AWS_ACCESS_KEY_ID=your-key-here
AWS_SECRET_ACCESS_KEY=your-secret-here
AWS_REGION=us-east-1
```

## Container Details

All services use official Docker images:
- **Airflow**: `apache/airflow:2.9.0-python3.10` with packages: egxpy, kafka-python, boto3, influxdb-client
- **PostgreSQL**: `postgres:15`
- **Kafka**: `confluentinc/cp-kafka:7.5.0`
- **Zookeeper**: `confluentinc/cp-zookeeper:7.5.0`
- **InfluxDB**: `influxdb:2.7`
- **Grafana**: `grafana/grafana:latest`
