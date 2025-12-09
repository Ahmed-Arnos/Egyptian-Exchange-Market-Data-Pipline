#!/bin/bash
# Egyptian Exchange Pipeline - Master Shutdown Script
# Gracefully stops all components

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

REPO_ROOT="/home/ahmed-elsaba/Git Repos/Egyptian-Exchange-Market-Data-Pipline"

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Egyptian Exchange Pipeline Shutdown${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Step 1: Stop Streaming Pipeline
echo -e "${BLUE}[1/3] Stopping Streaming Pipeline${NC}"
echo "--------------------------------------"

PRODUCER_PID=$(ps aux | grep producer_kafka.py | grep -v grep | awk '{print $2}')
CONSUMER_PID=$(ps aux | grep consumer_snowflake.py | grep -v grep | awk '{print $2}')

if [ -n "$PRODUCER_PID" ]; then
    echo "Stopping Kafka Producer (PID: $PRODUCER_PID)..."
    kill -SIGTERM "$PRODUCER_PID" 2>/dev/null || true
    sleep 2
    
    # Force kill if still running
    if ps -p "$PRODUCER_PID" > /dev/null 2>&1; then
        echo "Force killing producer..."
        kill -9 "$PRODUCER_PID" 2>/dev/null || true
    fi
    echo -e "${GREEN}✓${NC} Producer stopped"
else
    echo -e "${YELLOW}⚠${NC} Producer not running"
fi

if [ -n "$CONSUMER_PID" ]; then
    echo "Stopping Kafka Consumer (PID: $CONSUMER_PID)..."
    kill -SIGTERM "$CONSUMER_PID" 2>/dev/null || true
    sleep 2
    
    # Force kill if still running
    if ps -p "$CONSUMER_PID" > /dev/null 2>&1; then
        echo "Force killing consumer..."
        kill -9 "$CONSUMER_PID" 2>/dev/null || true
    fi
    echo -e "${GREEN}✓${NC} Consumer stopped"
else
    echo -e "${YELLOW}⚠${NC} Consumer not running"
fi

echo ""

# Step 2: Stop Airflow (if running in Docker)
echo -e "${BLUE}[2/3] Stopping Airflow${NC}"
echo "--------------------------------------"

cd "${REPO_ROOT}/infrastructure/docker"

if docker ps | grep airflow > /dev/null; then
    echo "Stopping Airflow services..."
    docker compose stop airflow airflow-scheduler 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Airflow stopped"
else
    echo -e "${YELLOW}⚠${NC} Airflow not running in Docker"
fi

echo ""

# Step 3: Stop Kafka and other Docker services
echo -e "${BLUE}[3/3] Stopping Docker Services${NC}"
echo "--------------------------------------"

read -p "Stop Kafka and other Docker services? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping Docker Compose services..."
    docker compose down
    echo -e "${GREEN}✓${NC} All Docker services stopped"
else
    echo "Keeping Docker services running"
fi

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Pipeline Shutdown Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""

# Show what's still running
echo "Remaining processes:"
STILL_RUNNING=0

if docker ps | grep -E "(kafka|zookeeper|airflow)" > /dev/null; then
    echo "Docker containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(kafka|zookeeper|airflow)" || true
    STILL_RUNNING=1
fi

if ps aux | grep -E "(producer|consumer)" | grep -v grep > /dev/null; then
    echo "Python processes:"
    ps aux | grep -E "(producer|consumer)" | grep -v grep || true
    STILL_RUNNING=1
fi

if [ "$STILL_RUNNING" -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All pipeline components stopped"
fi

echo ""
echo "To restart: ./scripts/start_pipeline.sh"
echo ""
