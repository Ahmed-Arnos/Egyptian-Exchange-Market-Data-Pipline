# Infrastructure Docker Setup

Complete data engineering infrastructure for EGX Market Data Pipeline.

## Services Included

### 📊 Real-time Streaming
- **Kafka** (9093) - Message broker
- **Zookeeper** (2181) - Kafka coordination
- **InfluxDB** (8086) - Time-series database
- **Grafana** (3000) - Dashboards and visualization
- **Kafka-UI** (8082) - Kafka monitoring

### 🔧 Batch Processing
- **Airflow** (8081) - Workflow orchestration
- **Postgres** (5432) - Airflow metadata store
- **Spark Master** (7077, 8080) - Distributed processing
- **Spark Worker** (8090) - Compute nodes
- **Jupyter** (8888) - Interactive development

### 💾 Storage
- **MinIO** (9000, 9001) - S3-compatible object storage

## Usage

### Start All Services
```bash
cd infrastructure/docker
docker-compose up -d
```

### Start Specific Services
```bash
# Streaming only
docker-compose up -d kafka zookeeper influxdb grafana

# Batch processing only
docker-compose up -d postgres airflow airflow-scheduler spark-master spark-worker

# Storage
docker-compose up -d minio
```

### Access Services
- Grafana: http://localhost:3000 (admin/admin)
- Airflow: http://localhost:8081 (admin/admin)
- Jupyter: http://localhost:8888 (token: admin)
- Kafka-UI: http://localhost:8082
- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
- Spark UI: http://localhost:8080

### Stop Services
```bash
docker-compose down
```

### Clean Volumes (CAUTION: Deletes all data)
```bash
docker-compose down -v
```

## Configuration

### Environment Variables
Create `.env` file in project root:
```bash
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

### Grafana Dashboard
Dashboard automatically provisioned from `grafana/provisioning/dashboards/egx-dashboard.json`

### Dockerfiles
- `dockerfile.airflow` - Airflow with Spark support
- `dockerfile.spark` - Spark 3.5.0 with Hadoop AWS
- `dockerfile.jupyter` - Jupyter with PySpark
