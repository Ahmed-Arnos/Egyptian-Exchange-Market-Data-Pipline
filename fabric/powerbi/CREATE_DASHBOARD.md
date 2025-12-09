# Creating Power BI Real-Time Dashboard for Egyptian Exchange

This guide shows how to create a professional trading dashboard in Power BI connected to your Fabric KQL Database.

## Prerequisites

- KQL Database with `MarketData` table populated
- Power BI Desktop (or use Power BI in Fabric workspace)
- Access to the Fabric workspace

## Option 1: Power BI Desktop (Recommended for Design)

### Step 1: Connect to KQL Database

1. Open Power BI Desktop
2. Click **Get Data** → **More**
3. Search for **Azure Data Explorer (Kusto)**
4. Click **Connect**
5. Enter connection details:
   - **Cluster**: `https://<your-workspace>.fabric.microsoft.com/`
   - **Database**: `egx_market_data`
6. Click **OK** and authenticate with your Microsoft account
7. Select **DirectQuery** mode for real-time data

### Step 2: Import Data Tables

Select these tables/queries to import:
- `MarketData` (main table)
- `LatestPrices` (materialized view)
- `DailyStats` (materialized view)
- `TopVolumeSymbols` (materialized view)

Or use custom KQL queries for each visual.

### Step 3: Create Dashboard Visuals

#### Visual 1: Market Overview (Card Grid)
- Visual: **Multi-row card**
- Query: `GetMarketOverview()`
- Fields: `symbol`, `close`, `price_change_pct`
- Format: Conditional formatting on `price_change_pct` (green > 0, red < 0)

#### Visual 2: Live Stock Prices (Line Chart)
- Visual: **Line chart**
- Query:
```kql
MarketData
| where timestamp > ago(7d)
| project timestamp, symbol, close
```
- X-axis: `timestamp`
- Y-axis: `close`
- Legend: `symbol`
- Enable auto-refresh (set to 1-5 minutes)

#### Visual 3: Top Performers (Bar Chart)
- Visual: **Clustered bar chart**
- Query: `GetTopPerformers(5)`
- X-axis: `price_change_pct`
- Y-axis: `symbol`
- Data colors: Gradient (green to yellow)

#### Visual 4: Trading Volume (Bar Chart)
- Visual: **Clustered column chart**
- Query: `GetVolumeBySymbol()`
- X-axis: `symbol`
- Y-axis: `total_volume`
- Top N filter: 10

#### Visual 5: Market Share (Pie Chart)
- Visual: **Donut chart**
- Query:
```kql
MarketData
| where timestamp > ago(24h)
| summarize total_volume = sum(volume) by symbol
| top 10 by total_volume desc
```
- Legend: `symbol`
- Values: `total_volume`

#### Visual 6: Price Range (Clustered Bar)
- Visual: **Clustered bar chart**
- Query:
```kql
MarketData
| where timestamp > ago(7d)
| summarize highest = max(high), lowest = min(low) by symbol
```
- Y-axis: `symbol`
- Values: `highest`, `lowest`

#### Visual 7: Latest Prices (Table)
- Visual: **Table**
- Query:
```kql
LatestPrices
| join kind=leftouter (
    MarketData | where timestamp > ago(1d) | summarize prev_close = first(close) by symbol
) on symbol
| extend price_change_pct = round((close - prev_close) / prev_close * 100, 2)
| project Symbol=symbol, Price=close, High=high, Low=low, Volume=volume, ["Change %"]=price_change_pct
```
- Conditional formatting: `Change %` (green > 0, red < 0)

### Step 4: Configure Refresh

1. Go to **File** → **Options and settings** → **Data source settings**
2. For the KQL Database connection, set refresh schedule
3. DirectQuery mode: Data refreshes automatically when visuals are viewed
4. For Import mode (not recommended for real-time): Set refresh to every 5-15 minutes

### Step 5: Publish to Fabric

1. Click **File** → **Publish** → **Publish to Power BI**
2. Select your Fabric workspace
3. Wait for upload to complete

## Option 2: Power BI in Fabric Workspace (Faster)

### Quick Start

1. In your Fabric workspace, click **New** → **Power BI report**
2. Click **Pick a published semantic model** → **KQL Database** → `egx_market_data`
3. Use the visual builder to create charts directly from KQL queries
4. Add visuals using the **Build a visual** pane
5. For each visual, click **More options** → **Edit query** to write custom KQL

### Enable Auto-Refresh

1. Open your published report in Fabric workspace
2. Click **File** → **Settings** → **Datasets**
3. Select your dataset
4. Under **Scheduled refresh**, enable **DirectQuery** real-time refresh
5. Set refresh interval: **1 minute** (minimum with Premium/Fabric capacity)

## Dashboard Design Tips

- **Dark Theme**: Use dark backgrounds (#1E1E1E) for professional financial look
- **Color Scheme**: 
  - Positive changes: Green (#4CAF50)
  - Negative changes: Red (#F44336)
  - Neutral: Gray/Blue (#2196F3)
- **Fonts**: Use clear, readable fonts (Segoe UI, Roboto)
- **Layout**: Place most important metrics at the top (Market Overview)
- **Interactivity**: Enable cross-filtering between visuals

## Dashboard Template

A complete Power BI template (`.pbit`) with all 7 visuals pre-configured is available at:
`fabric/powerbi/egx_dashboard_template.pbit`

To use:
1. Open in Power BI Desktop
2. Enter your KQL Database connection details
3. Customize colors/layout as needed
4. Publish to your workspace

## Mobile Layout

For mobile viewing:
1. In Power BI Desktop, go to **View** → **Mobile layout**
2. Arrange visuals in vertical stack
3. Prioritize: Latest Prices Table, Market Overview, Live Prices Chart

## Troubleshooting

### Data not refreshing
- Check DirectQuery connection to KQL Database
- Verify Event Stream is actively ingesting data
- Check KQL Database for recent `ingestion_time` values

### Visuals loading slowly
- Reduce time range (use `ago(1d)` instead of `ago(7d)`)
- Add materialized views in KQL for heavy aggregations
- Use summarized data instead of raw `MarketData` table

### Authentication errors
- Ensure you have Reader/Viewer permissions on the KQL Database
- Re-authenticate in Power BI Desktop: Data source settings → Edit permissions

## Advanced: Streaming Datasets (Alternative)

For ultra-low latency (< 1 minute refresh), consider using Power BI Streaming Datasets:
1. Create a Power BI streaming dataset via REST API
2. Modify `producer.py` to also push to Power BI REST API
3. Use streaming tiles in dashboard

This bypasses KQL Database for visualization but requires dual-write logic.

## References

- [Power BI and KQL Database](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/power-bi-data-connector)
- [DirectQuery for KQL](https://learn.microsoft.com/en-us/power-bi/connect-data/service-dataset-modes-understand#directquery-mode)
- [Power BI Auto-Refresh](https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-data)
