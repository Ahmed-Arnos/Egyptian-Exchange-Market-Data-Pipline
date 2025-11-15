"""Streaming consumer for Twelvedata API - fetches Egyptian stock market data at regular intervals.

This script polls the Twelvedata API for time-series data (e.g., 1-minute OHLCV bars)
for Egyptian stocks and can optionally produce events to a Kafka topic or write to local storage.

Usage:
  # Fetch latest 1-minute bars for a symbol and print to stdout
  python extract/twelvedata/stream_consumer.py --symbol COMM --interval 1min

  # Poll every 60 seconds and write to JSON files
  python extract/twelvedata/stream_consumer.py --symbol COMM --interval 1min --poll-interval 60 --outdir extract/twelvedata/raw

  # Fetch multiple symbols
  python extract/twelvedata/stream_consumer.py --symbol COMM,EKHO,SWDY --interval 1min --poll-interval 60

Environment variables:
  TWELVEDATA_API_KEY: API key for Twelvedata (required if not passed via --api-key)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

LOG = logging.getLogger("twelvedata.stream")


def fetch_time_series(
    api_key: str,
    symbol: str,
    interval: str = "1min",
    country: str = "Egypt",
    outputsize: int = 1,
    format: str = "JSON",
) -> dict:
    """Fetch time-series data from Twelvedata API.
    
    Args:
        api_key: Twelvedata API key
        symbol: Stock symbol (e.g., COMM, EKHO, SWDY)
        interval: Time interval (1min, 5min, 15min, 30min, 1h, etc.)
        country: Country filter (default: Egypt)
        outputsize: Number of data points to return
        format: Response format (JSON or CSV)
    
    Returns:
        Parsed JSON response as a dict
    """
    url = "https://api.twelvedata.com/time_series"
    params = {
        "apikey": api_key,
        "symbol": symbol,
        "interval": interval,
        "country": country,
        "outputsize": outputsize,
        "format": format,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    if format == "JSON":
        return resp.json()
    else:
        return {"raw_csv": resp.text}


def save_event(outdir: Path, symbol: str, data: dict):
    """Save a single time-series event to a JSON file."""
    outdir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    filename = f"{symbol}_{ts.replace(':', '-')}.json"
    path = outdir / filename
    with path.open("w") as f:
        json.dump(data, f, indent=2)
    LOG.info("Saved event to %s", path)


def main():
    parser = argparse.ArgumentParser(description="Stream Egyptian stock data from Twelvedata API")
    parser.add_argument("--api-key", default=None, help="Twelvedata API key (or set TWELVEDATA_API_KEY)")
    parser.add_argument("--symbol", required=True, help="Stock symbol(s), comma-separated (e.g., COMM,EKHO)")
    parser.add_argument("--interval", default="1min", help="Time interval (1min, 5min, etc.)")
    parser.add_argument("--country", default="Egypt", help="Country filter")
    parser.add_argument("--outputsize", type=int, default=1, help="Number of data points per request")
    parser.add_argument("--poll-interval", type=int, default=0, help="Poll interval in seconds (0 = run once and exit)")
    parser.add_argument("--outdir", default=None, help="Directory to save JSON events (optional)")
    parser.add_argument("--format", default="JSON", choices=["JSON", "CSV"], help="Response format")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    api_key = args.api_key or os.environ.get("TWELVEDATA_API_KEY")
    if not api_key:
        LOG.error("API key required. Set TWELVEDATA_API_KEY env var or pass --api-key")
        raise SystemExit(2)

    symbols = [s.strip() for s in args.symbol.split(",")]
    outdir = Path(args.outdir) if args.outdir else None

    LOG.info("Starting stream consumer for symbols=%s interval=%s", symbols, args.interval)

    while True:
        for symbol in symbols:
            try:
                LOG.info("Fetching %s...", symbol)
                data = fetch_time_series(
                    api_key=api_key,
                    symbol=symbol,
                    interval=args.interval,
                    country=args.country,
                    outputsize=args.outputsize,
                    format=args.format,
                )
                
                # Log the response
                if args.format == "JSON":
                    LOG.info("Received data for %s: %s", symbol, json.dumps(data, indent=2))
                else:
                    LOG.info("Received CSV data for %s:\n%s", symbol, data.get("raw_csv", ""))

                # Save to disk if outdir is specified
                if outdir:
                    save_event(outdir, symbol, data)

            except requests.RequestException as e:
                LOG.exception("Failed to fetch %s: %s", symbol, e)
            except Exception as e:
                LOG.exception("Unexpected error processing %s: %s", symbol, e)

        if args.poll_interval <= 0:
            LOG.info("Single run complete, exiting")
            break

        LOG.info("Sleeping for %d seconds...", args.poll_interval)
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    main()
