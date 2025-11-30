#!/usr/bin/env bash
# Quick setup script for the real-time streaming pipeline
# Run this after cloning the repo

set -e

echo "=== EGX Real-time Streaming Pipeline Setup ==="
echo ""

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Start services
echo "📦 Starting services (Kafka, Zookeeper, InfluxDB, Grafana, MinIO)..."
cd "$(dirname "$0")/../../infrastructure/docker"
docker compose -f docker-compose.dev.yml up -d

echo ""
echo "⏳ Waiting 20 seconds for services to initialize..."
sleep 20

# Check services
echo ""
echo "✅ Services status:"
docker compose -f docker-compose.dev.yml ps

# Go back to project root
cd "$(dirname "$0")/../.."

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo ""
    echo "⚠️  Virtual environment not found. Creating .venv..."
    python3 -m venv .venv
fi

# Activate venv and install dependencies
echo ""
echo "📦 Installing Python dependencies..."
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Start the real-time consumer:"
echo "   source .venv/bin/activate"
echo "   python extract/realtime/consumer_influxdb.py --topic egx_market_data --bootstrap localhost:9093 &"
echo ""
echo "2. Start the producer (in another terminal):"
echo "   source .venv/bin/activate"
echo "   python extract/egxpy_streaming/producer_kafka.py --symbols COMI,ETEL --interval Daily --n-bars 10 --bootstrap-servers localhost:9093"
echo ""
echo "3. View the Grafana dashboard:"
echo "   Open: http://localhost:3000"
echo "   Login: admin / admin"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Available Services:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Grafana:    http://localhost:3000  (admin / admin)"
echo "  InfluxDB:   http://localhost:8086  (admin / admin123456)"
echo "  Kafka UI:   http://localhost:8080"
echo "  MinIO:      http://localhost:9001  (minioadmin / minioadmin)"
echo ""
echo "To stop services:"
echo "  cd infrastructure/docker && docker compose -f docker-compose.dev.yml down"
echo ""
