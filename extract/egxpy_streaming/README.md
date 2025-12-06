# EGXpy Streaming Consumer

A Python-based streaming consumer for fetching Egyptian Exchange (EGX) market data using the **egxpy** library.

## Overview

This consumer provides access to:
- **Daily/Weekly/Monthly OHLCV data** - Historical open/high/low/close/volume data
- **Intraday minute-level data** - 1-minute, 5-minute, or 30-minute granularity
- **Continuous polling mode** - Stream data at configurable intervals

The egxpy library uses **TradingView** as the data source and works in "nologin" mode (no authentication required, though data may be limited).

## Features

✅ **Free-tier access** - No API key or subscription required  
✅ **Egyptian market focus** - Native support for EGX stocks  
✅ **Multiple intervals** - Daily, weekly, monthly, and intraday (1/5/30 minute)  
✅ **Streaming mode** - Continuous polling with configurable intervals  
✅ **JSON output** - Structured data saved to files  
✅ **Error handling** - Robust retry logic and logging  

## Installation

The egxpy package is installed from GitHub:

```bash
pip install git+https://github.com/egxlytics/egxpy.git
```

Dependencies (auto-installed):
- pandas, numpy, holidays, retry
- tvdatafeed (TradingView data feed library)

## Usage

### Fetch Daily Data (Last N Bars)

```bash
# Single fetch: last 10 bars for COMI and ETEL
python extract/egxpy_streaming/consumer.py \
  --symbols COMI,ETEL \
  --interval Daily \
  --n-bars 10

# Custom output directory
python extract/egxpy_streaming/consumer.py \
  --symbols COMI \
  --interval Daily \
  --n-bars 20 \
  --outdir /tmp/egx_data
```

### Continuous Streaming Mode

```bash
# Poll every 60 seconds for latest data
python extract/egxpy_streaming/consumer.py \
  --symbols COMI,ETEL,SWDY \
  --interval Daily \
  --n-bars 5 \
  --poll-interval 60
```

### Fetch Intraday Data

```bash
# 5-minute bars for a specific date range
python extract/egxpy_streaming/consumer.py \
  --symbols COMI,ETEL \
  --interval "5 Minute" \
  --start-date 2025-01-20 \
  --end-date 2025-01-20

# 1-minute intraday data
python extract/egxpy_streaming/consumer.py \
  --symbols COMI \
  --interval "1 Minute" \
  --start-date 2025-01-20 \
  --end-date 2025-01-20
```

### Weekly/Monthly Data

```bash
# Last 52 weeks
python extract/egxpy_streaming/consumer.py \
  --symbols COMI \
  --interval Weekly \
  --n-bars 52

# Last 12 months
python extract/egxpy_streaming/consumer.py \
  --symbols COMI \
  --interval Monthly \
  --n-bars 12
```

## Command-Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--symbols` | ✅ Yes | - | Comma-separated stock symbols (e.g., `COMI,ETEL`) |
| `--exchange` | No | `EGX` | Exchange name |
| `--interval` | No | `Daily` | Data interval: `Daily`, `Weekly`, `Monthly`, `1 Minute`, `5 Minute`, `30 Minute` |
| `--n-bars` | No | `10` | Number of recent bars (for Daily/Weekly/Monthly) |
| `--start-date` | Conditional | - | Start date for intraday (YYYY-MM-DD, required for intraday) |
| `--end-date` | Conditional | - | End date for intraday (YYYY-MM-DD, required for intraday) |
| `--poll-interval` | No | - | If set, poll every N seconds (streaming mode) |
| `--outdir` | No | `extract/egxpy_streaming/raw` | Output directory for JSON files |
| `--log-level` | No | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Popular Egyptian Stock Symbols

| Symbol | Company Name |
|--------|-------------|
| `COMI` | Commercial International Bank (CIB) |
| `ETEL` | Egyptian Company for Mobile Services (Etisalat Misr) |
| `HELI` | Heliopolis Housing & Development |
| `SWDY` | El Sewedy Electric Company |
| `OCDI` | Orascom Construction Industries |
| `JUFO` | Juhayna Food Industries |
| `EGAS` | Egyptian Gas Company |
| `SKPC` | Sidi Kerir Petrochemicals Company |

For a full list, visit the [EGX official website](https://www.egx.com.eg/en/HomePage.aspx).

## Output Format

Data is saved as JSON files with the naming pattern: `{SYMBOL}_{TIMESTAMP}.json`

### Daily/Weekly/Monthly Output

```json
[
  {
    "symbol": "EGX:COMI",
    "open": 110.39,
    "high": 110.5,
    "low": 108.5,
    "close": 108.5,
    "volume": 1600086.0
  },
  ...
]
```

### Intraday Output

Similar structure but with minute-level timestamps in the index (converted to JSON).

## Data Source

egxpy fetches data from **TradingView** using the `tvdatafeed` library. The "nologin" method is used, which:
- ✅ Requires no authentication
- ✅ Provides free access to market data
- ⚠️ May have rate limits or data delays
- ⚠️ Data availability depends on TradingView's coverage

## Limitations

1. **No login mode**: Data may be limited compared to authenticated access
2. **Intraday date range**: May return empty results for recent dates (data availability depends on TradingView)
3. **Rate limiting**: High-frequency polling may be throttled
4. **No real-time streaming**: Uses polling-based approach (recommend 60+ second intervals)

## Troubleshooting

### Empty DataFrame / No Data Returned

**Symptom**: `WARNING No data returned for {SYMBOL}`

**Possible Causes**:
1. Symbol not available on TradingView
2. Date range outside available data (for intraday)
3. Weekend/market holiday (no trading data)
4. Rate limiting from TradingView

**Solutions**:
- Verify symbol exists: Check EGX website or TradingView
- For intraday: Try a date range 2-3 days in the past
- Increase poll interval to 60+ seconds
- Use Daily interval instead of intraday

### Import Error: `egxpy.download` could not be resolved

**Symptom**: Pylance/IDE shows import error

**Solution**: This is a false positive - egxpy is installed from GitHub, not PyPI. The code will run correctly. To suppress the warning, add this to `.vscode/settings.json`:

```json
{
  "python.analysis.extraPaths": [".venv/lib/python3.12/site-packages"]
}
```

## Integration with Pipeline

This consumer is designed as the **streaming extraction layer** for the pipeline:

```
egxpy_streaming (this)
  ↓
Bronze Layer (S3 - raw JSON)
  ↓
Kafka Topics (real-time streaming)
  ↓
Spark Streaming (transformations)
  ↓
Silver Layer (cleaned/validated)
  ↓
dbt (batch transformations)
  ↓
Gold Layer (Snowflake warehouse)
```

### Next Steps

1. **Kafka Producer**: Publish fetched data to Kafka topics
2. **Bronze Storage**: Upload JSON files to S3
3. **Spark Consumer**: Read from Kafka, apply transformations
4. **Schema Validation**: Add Pydantic models for data quality

## Development

### Run with Debug Logging

```bash
python extract/egxpy_streaming/consumer.py \
  --symbols COMI \
  --interval Daily \
  --n-bars 5 \
  --log-level DEBUG
```

### Test Different Symbols

```bash
# Test multiple symbols to find which are available
for symbol in COMI ETEL HELI SWDY OCDI; do
  echo "Testing $symbol..."
  python extract/egxpy_streaming/consumer.py \
    --symbols $symbol \
    --interval Daily \
    --n-bars 1 \
    --log-level WARNING
done
```

## References

- **egxpy Documentation**: https://egxlytics.github.io/egxpy/
- **EGX Official Website**: https://www.egx.com.eg/
- **TradingView**: https://www.tradingview.com/markets/stocks-egypt/market-movers/
