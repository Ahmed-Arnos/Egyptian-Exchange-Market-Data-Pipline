# 🚀 Real-time Streaming Pipeline - Setup Guide for Teammates

## What's New?

We now have **TWO parallel pipelines**:

### 1. **Real-time Pipeline** (NEW! 📊)
```
EGX API → Kafka → InfluxDB → Grafana
```
- **Purpose**: Live stock price monitoring with dashboards
- **Auto-refresh**: Every 5 seconds
- **View**: http://localhost:3000 (Grafana dashboard)

### 2. **Batch Pipeline** (Existing 📦)
```
EGX API → Kafka → S3 → Spark/dbt → Snowflake → Power BI
```
- **Purpose**: Historical analysis, reports, ML models
- **Storage**: S3 bucket with date/symbol partitioning

**Both consumers read from the same Kafka topic** - they run in parallel!

---

## 🏃 Quick Start (5 Minutes)

### Step 1: Pull Latest Code
```bash
cd Egyptian-Exchange-Market-Data-Pipline
git checkout dev-test
git pull origin dev-test
```

### Step 2: Run Setup Script
```bash
./setup_streaming.sh
```

This will:
- ✅ Start Docker services (Kafka, InfluxDB, Grafana, MinIO)
- ✅ Install Python dependencies
- ✅ Show you next steps

### Step 3: Start Real-time Consumer
```bash
source .venv/bin/activate

python extract/realtime/consumer_influxdb.py \
  --topic egx_market_data \
  --bootstrap localhost:9093 &
```

### Step 4: Start Producer
```bash
# In another terminal
source .venv/bin/activate

python extract/egxpy_streaming/producer_kafka.py \
  --symbols COMI,ETEL,HELI \
  --interval Daily \
  --n-bars 20 \
  --poll-interval 60 \
  --bootstrap-servers localhost:9093
```

### Step 5: View Dashboard
Open **http://localhost:3000** in your browser

- Username: `admin`
- Password: `admin`
- Dashboard loads automatically!

---

## 📊 What You'll See in Grafana

1. **Stock Prices Chart** - Real-time close prices
2. **Trading Volume** - Bar chart of trading volume
3. **OHLC Candlestick** - Open/High/Low/Close view
4. **Live Stats**:
   - Latest Price
   - Total Volume (5 min)
   - Active Symbols
   - Data Points

Dashboard refreshes **every 5 seconds** automatically!

---

## 🔧 Available Services

| Service | Port | URL | Credentials |
|---------|------|-----|-------------|
| **Grafana** | 3000 | http://localhost:3000 | admin / admin |
| **InfluxDB** | 8086 | http://localhost:8086 | admin / admin123456 |
| **Kafka UI** | 8080 | http://localhost:8080 | - |
| **MinIO** | 9001 | http://localhost:9001 | minioadmin / minioadmin |

---

## 🛑 Stop Services

```bash
cd infrastructure/docker
docker compose -f docker-compose.dev.yml down
```

---

## 🐛 Troubleshooting

### "Docker is not running"
```bash
# Start Docker Desktop (Ubuntu/Mac)
sudo systemctl start docker

# Or on Mac with Docker Desktop
open /Applications/Docker.app
```

### "Port already in use"
```bash
# Check what's using the port
sudo lsof -i :3000  # For Grafana
sudo lsof -i :9093  # For Kafka

# Kill the process
kill -9 <PID>
```

### "No data in Grafana"
1. Check if producer is running: `ps aux | grep producer_kafka`
2. Check if consumer is running: `ps aux | grep consumer_influxdb`
3. Check InfluxDB has data:
   - Open http://localhost:8086
   - Login: admin / admin123456
   - Go to Data Explorer
   - Query: `from(bucket: "market_data") |> range(start: -1h)`

### "Cannot connect to InfluxDB"
```bash
# Restart InfluxDB
docker restart influxdb

# Check logs
docker logs influxdb
```

---

## 📚 Documentation

- **Real-time Pipeline**: `extract/realtime/README.md`
- **Batch Pipeline**: `extract/streaming/README.md`
- **Main Architecture**: `README.md`
- **Streaming Docs**: `docs/STREAMING_ARCHITECTURE.md`

---

## 🤝 Working Together

**Branch**: `dev-test`

```bash
# Always pull before starting work
git pull origin dev-test

# Create feature branch
git checkout -b feature/your-name-description

# Push and create PR to dev-test
git push origin feature/your-name-description
```

---

## 💡 Tips

1. **Run both consumers** to populate both pipelines:
   ```bash
   # Terminal 1: Real-time (InfluxDB)
   python extract/realtime/consumer_influxdb.py --topic egx_market_data --bootstrap localhost:9093 &
   
   # Terminal 2: Batch (S3)
   python extract/streaming/consumer_kafka.py --topic egx_market_data --bucket egx-data-bucket --use-aws &
   ```

2. **Use different symbols** for testing:
   - COMI, ETEL, HELI, SWDY (main stocks)
   - Add more in producer `--symbols` flag

3. **Adjust refresh interval** in producer:
   - `--poll-interval 60` = fetch every 60 seconds
   - `--poll-interval 300` = fetch every 5 minutes

---

## ❓ Questions?

Ask in the team channel or check:
- `extract/realtime/README.md` for detailed real-time setup
- `extract/streaming/README.md` for batch pipeline details

---

**Happy Streaming! 📈**
