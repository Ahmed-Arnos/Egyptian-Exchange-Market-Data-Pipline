# Egyptian Exchange Streaming Pipeline - Microsoft Fabric Implementation

This implementation replaces the Docker-based architecture (Kafka + Spark + InfluxDB + Grafana) with Microsoft Fabric's unified analytics platform.

## Architecture Overview

```
egxpy API → Python Producer → Fabric Event Streams → KQL Database → Power BI Dashboard
```

### Components

1. **Event Streams Producer** (`eventstream/producer.py`)
   - Fetches real-time market data from Egyptian Exchange via egxpy
   - Sends events to Fabric Event Streams using REST API
   - Handles 26 companies with 100 historical bars each

2. **KQL Database** (`kql/schema.kql`)
   - Eventhouse database for time-series market data storage
   - Optimized for real-time analytics and queries
   - Auto-indexed and partitioned by ingestion time

3. **Event Streams**
   - Custom App source receives market data
   - No-code transformation and routing
   - Direct ingestion to KQL Database destination

4. **Power BI Dashboard** (`powerbi/egx_dashboard.pbix`)
   - Real-time visualization of market data
   - Professional trading dashboard design
   - Auto-refresh with live data

## Prerequisites

- Microsoft Fabric Workspace with Contributor access
- Fabric Capacity (F4 or higher recommended)
- Python 3.10+
- Required Python packages: `requests`, `egxpy`

## Setup Instructions

### 1. Create Fabric Resources

#### Create KQL Database
1. Navigate to your Fabric workspace
2. Switch to **Real-Time Intelligence** experience
3. Click **New** → **Eventhouse**
4. Name it `egx_eventhouse`
5. Create a KQL Database inside: `egx_market_data`

#### Create Event Stream
1. In the same workspace, click **New** → **Eventstream**
2. Name it `egx_stream`
3. Add source: **Custom App**
4. Copy the connection string and event hub name

### 2. Configure KQL Database Schema

Run the KQL script from `kql/schema.kql` in your KQL Database to create:
- `MarketData` table for OHLCV data
- Ingestion mapping for JSON data
- Materialized views for aggregations

### 3. Configure Event Stream Pipeline

1. Open `egx_stream` eventstream
2. Add **Custom App** source (already created)
3. Add transformation (optional): Filter, Aggregate, or Group by
4. Add **KQL Database** destination:
   - Database: `egx_market_data`
   - Table: `MarketData`
   - Data format: JSON
   - Mapping: `MarketDataMapping`

### 4. Run the Producer

```bash
cd fabric/eventstream
pip install -r requirements.txt
python producer.py
```

Update `config.json` with your Event Streams connection details:
- Event Hub connection string
- Event Hub name
- Companies list
- Polling interval

### 5. Create Power BI Dashboard

1. Open Power BI Desktop
2. Connect to data source: **KQL Database**
3. Select `egx_eventhouse` → `egx_market_data`
4. Import pre-built dashboard from `powerbi/egx_dashboard.pbix`
5. Publish to your Fabric workspace
6. Enable auto-refresh (up to 1 minute intervals with Premium)

## Data Flow

1. **Producer**: Polls egxpy API every 3 minutes (180s)
2. **Event Streams**: Receives JSON events via Custom App endpoint
3. **KQL Database**: Ingests events into `MarketData` table
4. **Power BI**: Queries KQL database and refreshes visualizations

## Advantages over Docker Setup

✅ **Unified Platform**: Single Microsoft Fabric workspace  
✅ **No Infrastructure Management**: Fully managed services  
✅ **Enterprise Security**: Azure AD integration, role-based access  
✅ **Scalability**: Auto-scaling event streams and KQL database  
✅ **Cost Effective**: Pay-per-use with Fabric capacity  
✅ **Power BI Integration**: Native real-time dashboards  
✅ **No Docker/Containers**: No disk space or container management issues  

## Monitoring

- **Event Streams Monitor**: View ingestion rate, lag, errors
- **KQL Query Performance**: Analyze query patterns and optimize
- **Power BI Metrics**: Track refresh duration and failures

## Cost Estimation

With F4 Capacity (4 CUs):
- Event Streams: Included in capacity
- KQL Database: Included in capacity (storage extra)
- Power BI: Included in capacity

Estimated: $500-800/month for F4 capacity (shared across all Fabric workloads)

## Troubleshooting

### Producer not sending events
- Check Event Hub connection string
- Verify egxpy API access
- Check network connectivity

### Events not appearing in KQL Database
- Verify Event Streams destination configuration
- Check ingestion mapping in KQL
- Review Event Streams error logs

### Power BI dashboard not refreshing
- Check dataset refresh schedule
- Verify KQL database connectivity
- Review Power BI service logs

## References

- [Microsoft Fabric Event Streams Documentation](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/overview)
- [KQL Database Documentation](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/create-database)
- [Power BI Real-Time Streaming](https://learn.microsoft.com/en-us/power-bi/connect-data/service-real-time-streaming)
