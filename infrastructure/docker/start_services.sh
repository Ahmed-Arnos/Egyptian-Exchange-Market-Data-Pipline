#!/bin/bash
# Quick setup script for Docker environment

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ENV_FILE="$SCRIPT_DIR/.env"

echo "======================================"
echo "  Docker Environment Setup"
echo "======================================"
echo ""

# Check if .env exists
if [ -f "$ENV_FILE" ]; then
    echo "✓ .env file found"
    
    # Check if AWS credentials are set
    if grep -q "AWS_ACCESS_KEY_ID=$" "$ENV_FILE" || grep -q "AWS_SECRET_ACCESS_KEY=$" "$ENV_FILE"; then
        echo ""
        echo "⚠️  WARNING: AWS credentials not configured in .env"
        echo ""
        echo "Please edit infrastructure/docker/.env and add your AWS credentials:"
        echo "  AWS_ACCESS_KEY_ID=your-key-here"
        echo "  AWS_SECRET_ACCESS_KEY=your-secret-here"
        echo ""
        read -p "Press Enter to continue anyway, or Ctrl+C to exit..."
    else
        echo "✓ AWS credentials configured"
    fi
else
    echo "✗ .env file not found"
    echo ""
    echo "Creating .env from .env.example..."
    cp "$SCRIPT_DIR/.env.example" "$ENV_FILE"
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  Please edit infrastructure/docker/.env and add your AWS credentials:"
    echo "  AWS_ACCESS_KEY_ID=your-key-here"
    echo "  AWS_SECRET_ACCESS_KEY=your-secret-here"
    echo ""
    exit 1
fi

echo ""
echo "Starting Docker services..."
echo ""

cd "$SCRIPT_DIR"
docker compose up -d

echo ""
echo "======================================"
echo "  Services Starting..."
echo "======================================"
echo ""
echo "Waiting for services to be ready (30 seconds)..."
sleep 10
echo "20 seconds remaining..."
sleep 10
echo "10 seconds remaining..."
sleep 10

echo ""
echo "======================================"
echo "  ✓ Services Started"
echo "======================================"
echo ""
echo "Access URLs:"
echo "  • Airflow:   http://localhost:8081 (admin/admin)"
echo "  • Grafana:   http://localhost:3000 (admin/admin)"
echo "  • Kafka UI:  http://localhost:8082"
echo "  • InfluxDB:  http://localhost:8086 (admin/admin123456)"
echo ""
echo "Next steps:"
echo "  1. Go to Airflow UI: http://localhost:8081"
echo "  2. Login with admin/admin"
echo "  3. Enable the DAG: egx_streaming_pipeline"
echo "  4. Trigger the DAG manually"
echo ""
echo "To view logs:"
echo "  docker compose logs -f [service-name]"
echo ""
echo "To stop services:"
echo "  docker compose down"
echo ""
