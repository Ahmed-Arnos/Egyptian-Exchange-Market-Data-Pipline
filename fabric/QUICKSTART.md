# Microsoft Fabric Implementation - Quick Start Guide

## 🚀 Overview

This implementation moves your Egyptian Exchange streaming pipeline to Microsoft Fabric, replacing the Docker-based stack (Kafka + Spark + InfluxDB + Grafana) with a unified cloud platform.

**Architecture:**
```
egxpy API → Python Producer → Event Streams → KQL Database → Power BI Dashboard
```

## 📁 Project Structure

```
fabric/
├── README.md                       # Architecture overview and benefits
├── QUICKSTART.md                   # This file - getting started
├── eventstream/
│   ├── producer.py                 # Python producer for Event Streams
│   ├── requirements.txt            # Python dependencies
│   ├── config.json.example         # Configuration template
│   ├── config.json                 # Your actual config (gitignored)
│   ├── run_producer.sh             # Quick-start script
│   └── DEPLOY_EVENTSTREAM.md       # Detailed Event Streams setup
├── kql/
│   ├── schema.kql                  # Database schema + mappings
│   └── sample_queries.kql          # Ready-to-use KQL queries
└── powerbi/
    └── CREATE_DASHBOARD.md         # Power BI dashboard guide
```

## ⚡ Quick Start (5 Steps)

### Step 1: Create Fabric Resources

1. Go to [Microsoft Fabric](https://app.fabric.microsoft.com)
2. Create or select a workspace
3. Switch to **Real-Time Intelligence** experience
4. Create:
   - **Eventhouse**: `egx_eventhouse`
   - **KQL Database**: `egx_market_data` (inside eventhouse)
   - **Eventstream**: `egx_stream`

### Step 2: Configure Event Stream

1. Open `egx_stream`
2. Add source: **Custom App**
3. Copy the **connection string** and **event hub name**
4. Keep this tab open - you'll configure the destination in Step 4

### Step 3: Setup KQL Database

1. Open KQL Database `egx_market_data`
2. Copy all commands from `fabric/kql/schema.kql`
3. Paste in KQL query editor and run
4. Verify: `MarketData` table and `MarketDataMapping` created

### Step 4: Connect Event Stream to KQL Database

1. Return to `egx_stream` eventstream
2. Add destination: **KQL Database**
3. Select database: `egx_market_data`
4. Table: `MarketData`
5. Data format: **JSON**
6. Ingestion mapping: `MarketDataMapping`
7. Click **Add**

### Step 5: Run Producer Locally

```bash
cd fabric/eventstream

# Copy config template
cp config.json.example config.json

# Edit config.json - add your Event Streams connection details
nano config.json  # or use any editor

# Run producer
./run_producer.sh
```

Producer will start sending market data every 3 minutes (configurable).

## 🎯 Verify Data Flow

### Check Event Stream
- In Event Stream canvas, click **Data insights**
- You should see events flowing (rate, throughput)

### Check KQL Database
```kql
// View latest ingested data
MarketData
| top 100 by ingestion_time desc

// Check data by symbol
MarketData
| summarize count() by symbol
| order by count_ desc
```

### Check Data Freshness
```kql
MarketData
| summarize last_ingestion = max(ingestion_time)
| extend freshness = now() - last_ingestion
```

## 📊 Create Power BI Dashboard

Follow the guide: `fabric/powerbi/CREATE_DASHBOARD.md`

Quick version:
1. Open Power BI Desktop
2. Connect to KQL Database: `egx_market_data`
3. Use queries from `fabric/kql/sample_queries.kql`
4. Create visuals (Market Overview, Live Prices, Top Performers, etc.)
5. Publish to your Fabric workspace
6. Enable auto-refresh (1-5 minutes)

## 🔧 Configuration

### Producer Settings (`config.json`)

```json
{
    "connection_string": "Endpoint=sb://...",
    "event_hub_name": "egx_stream",
    "symbols": ["COMI", "ETEL", "SWDY", ...],
    "exchange": "EGX",
    "interval": "Daily",
    "n_bars": 100,
    "poll_interval": 180
}
```

- `connection_string`: From Event Streams Custom App source
- `event_hub_name`: Event stream name
- `symbols`: Stock symbols to track
- `n_bars`: Historical bars to fetch per symbol
- `poll_interval`: Seconds between API polls (180 = 3 minutes)

### Environment Variables (Alternative to config.json)

```bash
export FABRIC_EVENTHUB_CONNECTION_STRING="Endpoint=sb://..."
export FABRIC_EVENTHUB_NAME="egx_stream"

python producer.py --symbols COMI,ETEL,SWDY --n-bars 100 --poll-interval 180
```

## 🎛️ Running Options

### Continuous Mode (Production)
```bash
python producer.py --config config.json
```

### Single Run (Testing)
```bash
python producer.py --config config.json --once
```

### Custom Symbols
```bash
python producer.py \
    --connection-string "Endpoint=sb://..." \
    --event-hub "egx_stream" \
    --symbols COMI,ETEL,SWDY,CIEB \
    --n-bars 50 \
    --poll-interval 300
```

## 📈 Sample Queries

### Market Overview
```kql
GetMarketOverview()
```

### Top 5 Performers
```kql
GetTopPerformers(5)
```

### Price History (Last 30 Days)
```kql
GetPriceHistory("COMI", 30)
```

### Volume Leaders
```kql
GetVolumeBySymbol()
| top 10 by total_volume desc
```

See `fabric/kql/sample_queries.kql` for 40+ ready-to-use queries.

## 🐛 Troubleshooting

### Producer Not Sending Events
```bash
# Test egxpy connection
python -c "from egxpy.download import get_OHLCV_data; print(get_OHLCV_data('COMI', 'EGX', 'Daily', 5))"

# Check Event Hub connection
# Look for "Successfully sent X events" in producer logs
```

### Events Not Reaching KQL Database
- Verify Event Stream destination is configured
- Check ingestion mapping: `MarketDataMapping` must exist
- View Event Stream errors in Azure portal logs

### KQL Query Errors
```kql
// Check table exists
.show tables

// Check mapping
.show table MarketData ingestion mappings

// View recent errors
.show ingestion failures
```

### Producer Crashes
```bash
# Check Python version (3.10+ required)
python --version

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Run with debug logging
python producer.py --config config.json 2>&1 | tee producer.log
```

## 💰 Cost Estimation

Using Fabric Capacity F4 (4 CUs):
- **Event Streams**: Included
- **KQL Database**: Included (storage charged separately)
- **Power BI**: Included
- **Estimated**: $500-800/month for F4

You can share this capacity across all Fabric workloads in your organization.

## 🔄 Migration from Docker Setup

Key differences:
| Docker Setup | Fabric Setup |
|-------------|--------------|
| Kafka | Event Streams (Kafka-compatible) |
| Spark Streaming | Event Streams transformations |
| InfluxDB | KQL Database |
| Grafana | Power BI |
| Local containers | Fully managed cloud |
| Manual scaling | Auto-scaling |
| Disk space issues | Cloud storage |

To run both in parallel:
1. Keep Docker setup on `main` branch
2. Run Fabric on `fabric-integration` branch
3. Compare results before switching

## 📚 Next Steps

- [ ] Add more symbols to `config.json`
- [ ] Create alerting with Fabric Activator (for price spikes)
- [ ] Schedule producer in Azure Container Instances or Azure Functions
- [ ] Add data quality monitoring queries
- [ ] Export data to OneLake for long-term storage
- [ ] Integrate with Azure DevOps for CI/CD

## 🆘 Getting Help

- **Event Streams**: [Documentation](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/overview)
- **KQL Database**: [Documentation](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/create-database)
- **Power BI**: [Documentation](https://learn.microsoft.com/en-us/power-bi/)
- **Fabric Community**: [Forum](https://community.fabric.microsoft.com/)

## 🎓 Graduation Project Notes

**For your December 13, 2025 presentation:**

1. **Demo Flow**:
   - Show Event Stream with live data flow
   - Run KQL queries showing real-time market data
   - Display Power BI dashboard with auto-refresh
   - Compare with Docker setup (highlight advantages)

2. **Key Talking Points**:
   - Unified platform vs. multi-container orchestration
   - Enterprise-ready (security, scaling, monitoring)
   - Cost-effective for production workloads
   - Real-time analytics with KQL
   - Professional dashboards with Power BI

3. **Architecture Diagram**:
   - Include in your presentation deck
   - Show data flow: API → Producer → Event Streams → KQL → Power BI
   - Highlight the replacement of 5 containers with 3 Fabric services

Good luck with your presentation! 🎉
