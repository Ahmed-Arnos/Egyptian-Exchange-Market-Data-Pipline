#!/bin/bash
# Egyptian Exchange Pipeline - Master Startup Script
# Starts all components: Kafka, Airflow, Streaming, and monitoring

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

REPO_ROOT="/home/ahmed-elsaba/Git Repos/Egyptian-Exchange-Market-Data-Pipline"

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Egyptian Exchange Pipeline Startup${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Function to check if a service is running
check_service() {
    local service_name=$1
    local check_command=$2
    
    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $service_name is running"
        return 0
    else
        echo -e "${RED}✗${NC} $service_name is not running"
        return 1
    fi
}

# Step 1: Start Docker services (Kafka, Airflow, etc.)
echo -e "${BLUE}[1/4] Starting Docker Infrastructure${NC}"
echo "--------------------------------------"
cd "${REPO_ROOT}/infrastructure/docker"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠${NC} No .env file found in infrastructure/docker/"
    echo "Creating .env from template..."
    if [ -f "${REPO_ROOT}/egx_dw/.env" ]; then
        # Copy Snowflake credentials from egx_dw/.env
        cp "${REPO_ROOT}/egx_dw/.env" .env
        echo "AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}" >> .env
        echo "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}" >> .env
        echo "POSTGRES_USER=airflow" >> .env
        echo "POSTGRES_PASSWORD=airflow" >> .env
        echo "POSTGRES_DB=airflow" >> .env
    else
        echo -e "${RED}✗${NC} Could not find egx_dw/.env to copy credentials"
        exit 1
    fi
fi

# Start Docker services
echo "Starting Kafka and Zookeeper..."
docker compose up -d zookeeper kafka

echo "Waiting for Kafka to be ready..."
sleep 10

check_service "Zookeeper" "docker ps | grep zookeeper | grep Up"
check_service "Kafka" "docker ps | grep kafka | grep Up"

echo ""

# Step 2: Start Streaming Pipeline (Producer + Consumer)
echo -e "${BLUE}[2/4] Starting Streaming Pipeline${NC}"
echo "--------------------------------------"
cd "${REPO_ROOT}"

# Check if streaming is already running
PRODUCER_RUNNING=$(ps aux | grep producer_kafka.py | grep -v grep | wc -l)
CONSUMER_RUNNING=$(ps aux | grep consumer_snowflake.py | grep -v grep | wc -l)

if [ "$PRODUCER_RUNNING" -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC} Producer already running (PID: $(ps aux | grep producer_kafka.py | grep -v grep | awk '{print $2}'))"
else
    echo "Starting streaming pipeline..."
    ./scripts/start_streaming.sh
fi

sleep 5

check_service "Kafka Producer" "ps aux | grep producer_kafka.py | grep -v grep"
check_service "Kafka Consumer" "ps aux | grep consumer_snowflake.py | grep -v grep"

echo ""

# Step 3: Start Airflow (Optional - can be Docker or standalone)
echo -e "${BLUE}[3/4] Airflow Status${NC}"
echo "--------------------------------------"

read -p "Start Airflow services? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "${REPO_ROOT}/infrastructure/docker"
    
    AIRFLOW_RUNNING=$(docker ps | grep airflow | wc -l)
    
    if [ "$AIRFLOW_RUNNING" -eq 0 ]; then
        echo "Starting Airflow (this may take a minute)..."
        docker compose up -d airflow-init
        sleep 20
        docker compose up -d airflow airflow-scheduler
        
        echo "Waiting for Airflow to be ready..."
        sleep 30
    else
        echo -e "${YELLOW}⚠${NC} Airflow already running"
    fi
    
    check_service "Airflow Webserver" "docker ps | grep airflow | grep -v scheduler | grep Up"
    check_service "Airflow Scheduler" "docker ps | grep airflow-scheduler | grep Up"
    
    echo ""
    echo -e "${GREEN}✓${NC} Airflow UI: http://localhost:8081"
    echo "  Username: admin"
    echo "  Password: admin"
else
    echo "Skipping Airflow startup"
fi

echo ""

# Step 4: Final Health Check
echo -e "${BLUE}[4/4] Running Health Check${NC}"
echo "--------------------------------------"

if [ -f "${REPO_ROOT}/scripts/monitoring/monitor_streaming.sh" ]; then
    "${REPO_ROOT}/scripts/monitoring/monitor_streaming.sh"
else
    echo -e "${YELLOW}⚠${NC} Health check script not found, skipping"
fi

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Pipeline Startup Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Active Services:"
echo "  - Kafka: localhost:9093"
echo "  - Kafka UI: http://localhost:8082"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
if docker ps | grep airflow > /dev/null; then
    echo "  - Airflow: http://localhost:8081 (admin/admin)"
fi
echo ""
echo "Monitoring:"
echo "  - Producer log: tail -f logs/producer.log"
echo "  - Consumer log: tail -f logs/consumer.log"
echo "  - Health check: ./scripts/monitoring/monitor_streaming.sh"
echo ""
echo "To stop: ./scripts/stop_pipeline.sh"
echo ""
