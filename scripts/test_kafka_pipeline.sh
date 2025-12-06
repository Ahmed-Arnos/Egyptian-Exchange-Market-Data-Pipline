#!/usr/bin/env bash
# Quick test script for Kafka producer/consumer pipeline

set -e

echo "=== EGX Kafka Pipeline Test ==="
echo ""

# Check if docker is running
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start services
echo "📦 Starting Kafka, Zookeeper, and MinIO..."
docker compose -f infrastructure/docker/docker-compose.dev.yml up -d

echo "⏳ Waiting 15 seconds for services to be ready..."
sleep 15

# Check services
echo ""
echo "✅ Checking services..."
docker compose -f infrastructure/docker/docker-compose.dev.yml ps

# Activate venv
echo ""
echo "🐍 Activating Python virtual environment..."
source .venv/bin/activate

# Set MinIO credentials
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
export AWS_REGION=us-east-1
export MINIO_ENDPOINT=http://localhost:9000

echo ""
echo "🚀 Starting Kafka consumer (background)..."
python extract/streaming/consumer_kafka.py \
  --topic egx_market_data \
  --bucket egx-data-bucket \
  --minio-endpoint http://localhost:9000 \
  --bootstrap localhost:9093 \
  --log-level INFO > consumer.log 2>&1 &

CONSUMER_PID=$!
echo "   Consumer PID: $CONSUMER_PID"

sleep 3

echo ""
echo "📡 Running EGXpy producer (fetch 5 bars for COMI, ETEL)..."
python extract/egxpy_streaming/producer_kafka.py \
  --symbols TMGH, PHAR, ORWE, MTIE, MPRC, INFI, HRHO, HELI, ETEL, EKHO, EGX30, COMI, CCAP, AMOC, ADIB \
  --interval Daily \
  --n-bars 5 \
  --topic egx_market_data \
  --bootstrap-servers localhost:9093 \
  --log-level INFO

sleep 2

python extract/egxpy_streaming/producer_kafka.py \
  --symbols EMFD, TAQA, SKPC, UNIT, ABUK, ALCN, BINV, CIEB, CIRA, CLHO, EAST, EFIC, EFID, EFIH, EGAL  \
  --interval Daily \
  --n-bars 5 \
  --topic egx_market_data \
  --bootstrap-servers localhost:9093 \
  --log-level INFO

echo ""
echo "⏳ Waiting 5 seconds for consumer to process..."
sleep 5

echo ""
echo "🛑 Stopping consumer..."
kill $CONSUMER_PID 2>/dev/null || true

echo ""
echo "📊 Consumer log:"
tail -20 consumer.log

echo ""
echo "✅ Test complete!"
echo ""
echo "To view data in MinIO:"
echo "  1. Open http://localhost:9001 in browser"
echo "  2. Login: minioadmin / minioadmin"
echo "  3. Browse bucket: egx-data-bucket/streaming/"
echo ""
echo "To view Kafka topics and messages:"
echo "  1. Open http://localhost:8080 in browser"
echo "  2. Navigate to Topics → egx_market_data"
echo "  3. View messages, partitions, and consumer groups"
echo ""
echo "To stop services:"
echo "  docker compose -f infrastructure/docker/docker-compose.dev.yml down"
