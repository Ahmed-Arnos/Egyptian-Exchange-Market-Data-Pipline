# 🇪🇬 Egyptian Exchange (EGX) Streaming Pipeline

Real-time streaming pipeline for Egyptian stock market data, inspired by TradingView's market overview.

## 📋 Architecture

```
┌─────────────┐      ┌───────┐      ┌───────────┐      ┌─────────┐
│ TradingView │ ───> │ Kafka │ ───> │ Processor │ ───> │ QuestDB │
│  (Source)   │      │       │      │           │      │         │
└─────────────┘      └───────┘      └───────────┘      └─────────┘
                                                              │
                                                              v
                                                        ┌─────────┐
                                                        │ Grafana │
                                                        └─────────┘
```

### Components

- **Producer**: Scrapes Egyptian stock data and publishes to Kafka
- **Kafka**: Message broker for real-time data streaming
- **Processor**: Consumes Kafka messages and stores in QuestDB
- **QuestDB**: High-performance time-series database
- **Grafana**: Beautiful visualizations and dashboards

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 4GB RAM minimum
- Ports available: 9092 (Kafka), 9000 (QuestDB), 3000 (Grafana)

### Launch Pipeline

```powershell
cd egx_streaming_pipeline
docker-compose up -d
```

### Access Services

- **QuestDB Console**: http://localhost:9000
- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **Dashboard URL**: http://localhost:3000/d/egx-market-overview

### Check Logs

```powershell
# Producer logs
docker logs egx-producer -f

# Processor logs
docker logs egx-processor -f

# All services
docker-compose logs -f
```

### Stop Pipeline

```powershell
docker-compose down

# Remove data volumes
docker-compose down -v
```

## 📊 Dashboard Features

### 📈 Panels

1. **Stock Prices Time Series** - Last hour price movements
2. **Top Gainers** - Stocks with highest % increase
3. **Top Losers** - Stocks with highest % decrease
4. **Most Active** - Highest trading volumes
5. **Market Value Distribution** - Pie chart of top 10 stocks
6. **Market Statistics** - Total stocks, avg change, volume, data points

### 🎨 Visualizations

- **Color-coded tables**: Green for gains, red for losses
- **Real-time updates**: 10-second refresh
- **Company names**: Full Egyptian company names displayed
- **Currency**: All prices in EGP (Egyptian Pounds)

## 📈 Tracked Stocks (25 EGX Companies)

| Ticker | Company Name |
|--------|--------------|
| COMI | Commercial International Bank (Egypt) |
| EKHO | El Kahera Housing |
| HRHO | Heliopolis Housing |
| BTFH | Beltone Financial Holding |
| PHDC | Palm Hills Developments |
| OCDI | Orascom Construction Industries |
| JUFO | Juhayna Food Industries |
| ETEL | Egyptian Company for Mobile Services |
| ESRS | Eastern Company S.A.E. |
| SWDY | El Swedy Electric |
| GTHE | GB Auto |
| TMGH | TMG Holding |
| ORTE | Oriental Weavers |
| ALCN | Alexandria Container and Cargo Handling |
| HELI | Heliopolis Company for Housing and Development |
| SVCE | South Valley Cement |
| MEPA | Medical Packaging Company |
| NCCW | Nasr Co. for Civil Works |
| ICID | International Company for Investment & Development |
| IFAP | International Agricultural Products |
| BONY | Bonyan for Development and Trade |
| NIPH | El Nasr Company for Intermediate Chemicals |
| TPCO | Tenth of Ramadan Pharmaceutical |
| CCAP | Credit Agricole Egypt |
| FWRY | Fawry for Banking Technology and Electronic Payments |

## 🔧 Configuration

### Environment Variables

**Producer** (`producer/.env`):
```env
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC=egx-stock-data
FETCH_INTERVAL=30  # seconds
```

**Processor** (`processor/.env`):
```env
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC=egx-stock-data
KAFKA_GROUP_ID=egx-processor-group
QUESTDB_HOST=questdb
QUESTDB_PORT=9000
```

## 📊 QuestDB Queries

```sql
-- View latest prices
SELECT * FROM egx_stock_prices 
ORDER BY timestamp DESC 
LIMIT 20;

-- Top gainers today
SELECT ticker, company_name, price_change_percent 
FROM egx_stock_prices 
WHERE timestamp IN (SELECT max(timestamp) FROM egx_stock_prices)
ORDER BY price_change_percent DESC 
LIMIT 10;

-- Total market volume
SELECT SUM(volume) as total_volume 
FROM egx_stock_prices 
WHERE timestamp IN (SELECT max(timestamp) FROM egx_stock_prices);

-- Average price change
SELECT AVG(price_change_percent) as avg_change 
FROM egx_stock_prices 
WHERE timestamp IN (SELECT max(timestamp) FROM egx_stock_prices);
```

## 🛠️ Development

### Local Testing (without Docker)

```powershell
# Install dependencies
cd producer
pip install -r requirements.txt

cd ../processor
pip install -r requirements.txt

# Start Kafka & QuestDB separately, then:
python producer/egx_producer.py
python processor/egx_processor.py
```

### Adding More Stocks

Edit `producer/egx_producer.py`:
```python
EGX_STOCKS = {
    "NEWCO": "New Company Name",
    # ... add more
}
```

## ⚠️ Important Notes

### Current Data Source
The producer currently uses **simulated data** because:
- TradingView requires JavaScript rendering (needs Selenium/Playwright)
- No free official EGX API available
- Demo purposes to show pipeline functionality

### For Production Use
Replace `fetch_stock_data()` in `egx_producer.py` with:

1. **Official EGX API** (if available with subscription)
2. **Selenium/Playwright** for TradingView scraping:
   ```python
   from selenium import webdriver
   driver = webdriver.Chrome()
   driver.get("https://www.tradingview.com/symbols/EGX-COMI/")
   ```
3. **Financial Data APIs**:
   - Alpha Vantage
   - IEX Cloud
   - Yahoo Finance (limited EGX coverage)

## 🎯 TradingView-Style Features

This pipeline replicates TradingView's Egypt market page features:

✅ **Top Gainers/Losers** - Color-coded tables
✅ **Most Active Stocks** - By volume
✅ **Real-time Price Charts** - Time series visualization
✅ **Market Statistics** - Total stocks, avg change, volume
✅ **Market Value Distribution** - Pie chart
✅ **Company Names** - Full Egyptian company names
✅ **Auto-refresh** - 10-second updates

## 🔄 Data Flow

1. **Producer** fetches stock data every 30 seconds
2. **Kafka** streams data in real-time
3. **Processor** consumes and stores in QuestDB
4. **Grafana** queries QuestDB and displays dashboards
5. **Auto-refresh** keeps data current

## 📈 Scaling

- **Increase stocks**: Add tickers to `EGX_STOCKS`
- **Faster updates**: Reduce `FETCH_INTERVAL`
- **More partitions**: Adjust Kafka `KAFKA_NUM_PARTITIONS`
- **Horizontal scaling**: Deploy multiple processor instances

## 🆘 Troubleshooting

### No data in Grafana
```powershell
# Check producer is running
docker logs egx-producer --tail=50

# Check processor
docker logs egx-processor --tail=50

# Verify QuestDB has data
# Open http://localhost:9000
# Run: SELECT COUNT(*) FROM egx_stock_prices;
```

### Kafka connection errors
```powershell
# Restart Kafka
docker-compose restart kafka

# Check Kafka health
docker exec egx-kafka kafka-topics.sh --list --bootstrap-server localhost:9092
```

### Grafana dashboard not loading
```powershell
# Restart Grafana
docker-compose restart grafana

# Check provisioning
docker exec egx-grafana ls /var/lib/grafana/dashboards
```

## 📝 License

MIT License - Feel free to use for educational/personal projects

## 🤝 Contributing

Contributions welcome! Especially:
- Real EGX data source integration
- Additional dashboard visualizations
- Performance optimizations
- More Egyptian stocks

---

**Built with** ❤️ **for the Egyptian Exchange market**
