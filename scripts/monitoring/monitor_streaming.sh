#!/bin/bash
"""
Streaming Pipeline Health Monitor
---------------------------------
Monitors the health of Kafka producer, consumer, and data flow.
Can be run manually or scheduled via cron.

Usage:
    ./monitor_streaming.sh [--alert]
    
Options:
    --alert    Send alerts if issues detected (requires email configuration)
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REPO_ROOT="/home/ahmed-elsaba/Git Repos/Egyptian-Exchange-Market-Data-Pipline"
LOG_DIR="${REPO_ROOT}/logs"
ALERT_MODE=false

# Parse arguments
if [[ "$1" == "--alert" ]]; then
    ALERT_MODE=true
fi

echo "========================================="
echo "EGX Streaming Pipeline Health Check"
echo "Time: $(date)"
echo "========================================="
echo ""

# Initialize counters
ISSUES_FOUND=0
WARNINGS_FOUND=0

# Check 1: Kafka Docker containers
echo "1. Checking Kafka infrastructure..."
ZOOKEEPER_STATUS=$(docker ps --filter "name=docker-zookeeper-1" --format "{{.Status}}" 2>/dev/null || echo "not found")
KAFKA_STATUS=$(docker ps --filter "name=docker-kafka-1" --format "{{.Status}}" 2>/dev/null || echo "not found")

if [[ "$ZOOKEEPER_STATUS" == *"Up"* ]]; then
    echo -e "${GREEN}✓${NC} Zookeeper: Running ($ZOOKEEPER_STATUS)"
else
    echo -e "${RED}✗${NC} Zookeeper: NOT RUNNING"
    ((ISSUES_FOUND++))
fi

if [[ "$KAFKA_STATUS" == *"Up"* ]]; then
    echo -e "${GREEN}✓${NC} Kafka: Running ($KAFKA_STATUS)"
else
    echo -e "${RED}✗${NC} Kafka: NOT RUNNING"
    ((ISSUES_FOUND++))
fi

echo ""

# Check 2: Producer process
echo "2. Checking Kafka producer..."
PRODUCER_PID=$(ps aux | grep producer_kafka.py | grep -v grep | awk '{print $2}')

if [ -n "$PRODUCER_PID" ]; then
    echo -e "${GREEN}✓${NC} Producer running (PID: $PRODUCER_PID)"
    
    # Check producer log for recent activity
    if [ -f "${LOG_DIR}/producer.log" ]; then
        LAST_PRODUCER_LOG=$(tail -1 "${LOG_DIR}/producer.log")
        echo "  Last log: ${LAST_PRODUCER_LOG:0:100}..."
        
        # Check for recent errors
        ERROR_COUNT=$(tail -100 "${LOG_DIR}/producer.log" | grep -i "error\|failed" | wc -l)
        if [ "$ERROR_COUNT" -gt 5 ]; then
            echo -e "${YELLOW}⚠${NC} Warning: $ERROR_COUNT errors in last 100 log lines"
            ((WARNINGS_FOUND++))
        fi
    fi
else
    echo -e "${RED}✗${NC} Producer NOT RUNNING"
    ((ISSUES_FOUND++))
fi

echo ""

# Check 3: Consumer process
echo "3. Checking Kafka consumer..."
CONSUMER_PID=$(ps aux | grep consumer_snowflake.py | grep -v grep | awk '{print $2}')

if [ -n "$CONSUMER_PID" ]; then
    echo -e "${GREEN}✓${NC} Consumer running (PID: $CONSUMER_PID)"
    
    # Check consumer log
    if [ -f "${LOG_DIR}/consumer.log" ]; then
        LAST_CONSUMER_LOG=$(tail -1 "${LOG_DIR}/consumer.log")
        echo "  Last log: ${LAST_CONSUMER_LOG:0:100}..."
        
        # Check for insert success messages
        RECENT_INSERTS=$(tail -100 "${LOG_DIR}/consumer.log" | grep "Inserted batch" | wc -l)
        echo "  Recent successful inserts: $RECENT_INSERTS (last 100 lines)"
        
        if [ "$RECENT_INSERTS" -eq 0 ]; then
            echo -e "${YELLOW}⚠${NC} Warning: No successful inserts in recent logs"
            ((WARNINGS_FOUND++))
        fi
        
        # Check for errors
        ERROR_COUNT=$(tail -100 "${LOG_DIR}/consumer.log" | grep -i "error\|failed" | wc -l)
        if [ "$ERROR_COUNT" -gt 5 ]; then
            echo -e "${YELLOW}⚠${NC} Warning: $ERROR_COUNT errors in last 100 log lines"
            ((WARNINGS_FOUND++))
        fi
    fi
else
    echo -e "${RED}✗${NC} Consumer NOT RUNNING"
    ((ISSUES_FOUND++))
fi

echo ""

# Check 4: Snowflake data freshness
echo "4. Checking Snowflake data..."
cd "${REPO_ROOT}/egx_dw"
source ../.venv-aws/bin/activate
export $(cat .env | grep -v '^#' | xargs)

SNOWFLAKE_CHECK=$(python -c "
import snowflake.connector
import os
from datetime import datetime, timedelta

try:
    conn = snowflake.connector.connect(
        account='LPDTDON-IU51056',
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse='COMPUTE_WH'
    )
    cursor = conn.cursor()
    
    # Check last 1 hour
    cursor.execute('''
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT COMPANY_ID) as companies,
            MAX(CREATED_AT) as latest_timestamp
        FROM EGX_OPERATIONAL_DB.OPERATIONAL.TBL_STOCK_PRICE
        WHERE DATA_SOURCE = 'STREAMING_API'
        AND CREATED_AT > DATEADD(hour, -1, CURRENT_TIMESTAMP())
    ''')
    
    row = cursor.fetchone()
    total, companies, latest = row[0], row[1], row[2]
    
    cursor.close()
    conn.close()
    
    print(f'{total}|{companies}|{latest}')
except Exception as e:
    print(f'ERROR|{str(e)}')
" 2>&1)

IFS='|' read -r TOTAL_RECORDS COMPANIES LATEST_TS <<< "$SNOWFLAKE_CHECK"

if [[ "$TOTAL_RECORDS" == "ERROR" ]]; then
    echo -e "${RED}✗${NC} Snowflake connection failed: $COMPANIES"
    ((ISSUES_FOUND++))
elif [ "$TOTAL_RECORDS" -eq 0 ]; then
    echo -e "${RED}✗${NC} No data in last hour!"
    ((ISSUES_FOUND++))
else
    echo -e "${GREEN}✓${NC} Data flowing: $TOTAL_RECORDS records from $COMPANIES companies"
    echo "  Latest record: $LATEST_TS"
fi

echo ""

# Check 5: Log file sizes
echo "5. Checking log files..."
if [ -f "${LOG_DIR}/producer.log" ]; then
    PRODUCER_SIZE=$(du -h "${LOG_DIR}/producer.log" | cut -f1)
    echo "  Producer log: $PRODUCER_SIZE"
    
    # Warn if log is too large (>100MB)
    PRODUCER_SIZE_BYTES=$(stat -c%s "${LOG_DIR}/producer.log")
    if [ "$PRODUCER_SIZE_BYTES" -gt 104857600 ]; then
        echo -e "${YELLOW}⚠${NC} Producer log is large (>100MB) - consider rotation"
        ((WARNINGS_FOUND++))
    fi
fi

if [ -f "${LOG_DIR}/consumer.log" ]; then
    CONSUMER_SIZE=$(du -h "${LOG_DIR}/consumer.log" | cut -f1)
    echo "  Consumer log: $CONSUMER_SIZE"
    
    CONSUMER_SIZE_BYTES=$(stat -c%s "${LOG_DIR}/consumer.log")
    if [ "$CONSUMER_SIZE_BYTES" -gt 104857600 ]; then
        echo -e "${YELLOW}⚠${NC} Consumer log is large (>100MB) - consider rotation"
        ((WARNINGS_FOUND++))
    fi
fi

echo ""

# Summary
echo "========================================="
echo "HEALTH CHECK SUMMARY"
echo "========================================="
echo "Issues found: $ISSUES_FOUND"
echo "Warnings: $WARNINGS_FOUND"

if [ "$ISSUES_FOUND" -eq 0 ] && [ "$WARNINGS_FOUND" -eq 0 ]; then
    echo -e "${GREEN}✓ All systems operational${NC}"
    exit 0
elif [ "$ISSUES_FOUND" -eq 0 ]; then
    echo -e "${YELLOW}⚠ System operational with warnings${NC}"
    exit 0
else
    echo -e "${RED}✗ Critical issues detected - pipeline may be down${NC}"
    
    if [ "$ALERT_MODE" = true ]; then
        echo ""
        echo "RECOMMENDED ACTIONS:"
        if [ -z "$PRODUCER_PID" ]; then
            echo "  - Restart producer: cd '$REPO_ROOT' && ./start_streaming.sh"
        fi
        if [ -z "$CONSUMER_PID" ]; then
            echo "  - Restart consumer: cd '$REPO_ROOT' && ./start_streaming.sh"
        fi
        if [[ "$KAFKA_STATUS" != *"Up"* ]]; then
            echo "  - Restart Kafka: docker compose -f infrastructure/docker/docker-compose.yml restart kafka"
        fi
    fi
    
    exit 1
fi
