#!/bin/bash
# Quick-start script for running the Fabric Event Streams producer locally

set -e

echo "================================================"
echo "Egyptian Exchange → Fabric Event Streams Producer"
echo "================================================"
echo ""

# Check if config exists
if [ ! -f "config.json" ]; then
    echo "❌ ERROR: config.json not found"
    echo ""
    echo "Please copy config.json.example to config.json and update with your:"
    echo "  - Fabric Event Streams connection string"
    echo "  - Event hub name"
    echo "  - Stock symbols to track"
    echo ""
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Starting producer in continuous mode..."
echo "Press Ctrl+C to stop"
echo ""
echo "================================================"
echo ""

# Run producer
python producer.py --config config.json
