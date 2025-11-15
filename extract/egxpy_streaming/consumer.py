#!/usr/bin/env python3
"""
EGXpy Streaming Consumer

Fetches Egyptian Exchange (EGX) market data using the egxpy library.
Supports both daily OHLCV data and intraday minute-level data.

Usage:
    # Fetch daily data (last 10 bars)
    python consumer.py --symbols COMI,ETEL --interval Daily --n-bars 10

    # Continuous polling mode (daily data)
    python consumer.py --symbols COMI,ETEL --interval Daily --n-bars 10 --poll-interval 60

    # Fetch intraday data (requires date range)
    python consumer.py --symbols COMI --interval "5 Minute" --start-date 2025-01-20 --end-date 2025-01-20

Environment Variables:
    None required - egxpy works in "nologin" mode by default (data may be limited)
"""

import argparse
import json
import logging
import sys
import time
from datetime import date, datetime
from pathlib import Path

from egxpy.download import get_OHLCV_data, get_EGX_intraday_data

LOG = logging.getLogger(__name__)


def fetch_daily_data(symbols: list[str], exchange: str, interval: str, n_bars: int) -> dict:
    """
    Fetch daily/weekly/monthly OHLCV data for multiple symbols.
    
    Args:
        symbols: List of ticker symbols (e.g., ['COMI', 'ETEL'])
        exchange: Exchange name (e.g., 'EGX')
        interval: Time interval - 'Daily', 'Weekly', or 'Monthly'
        n_bars: Number of most recent bars to fetch
    
    Returns:
        Dictionary mapping symbol to DataFrame
    """
    results = {}
    
    for symbol in symbols:
        try:
            LOG.info(f"Fetching {interval} data for {symbol} (last {n_bars} bars)...")
            df = get_OHLCV_data(symbol, exchange, interval, n_bars)
            
            if df.empty:
                LOG.warning(f"No data returned for {symbol}")
            else:
                LOG.info(f"Retrieved {len(df)} rows for {symbol}")
                results[symbol] = df
                
        except Exception as e:
            LOG.error(f"Failed to fetch {symbol}: {e}")
            
    return results


def fetch_intraday_data(symbols: list[str], interval: str, start_date: date, end_date: date) -> dict:
    """
    Fetch intraday minute-level data for Egyptian stocks.
    
    Args:
        symbols: List of ticker symbols
        interval: Intraday interval - '1 Minute', '5 Minute', or '30 Minute'
        start_date: Start date
        end_date: End date (inclusive)
    
    Returns:
        DataFrame with columns for each symbol
    """
    try:
        LOG.info(f"Fetching {interval} intraday data for {symbols} from {start_date} to {end_date}...")
        df = get_EGX_intraday_data(symbols, interval, start_date, end_date)
        
        if df.empty:
            LOG.warning("No intraday data returned")
            return {}
        else:
            LOG.info(f"Retrieved {len(df)} rows with columns: {df.columns.tolist()}")
            return {"intraday": df}
            
    except Exception as e:
        LOG.error(f"Failed to fetch intraday data: {e}")
        return {}


def save_data(data: dict, outdir: Path, timestamp: str) -> None:
    """
    Save fetched data to JSON files.
    
    Args:
        data: Dictionary mapping symbol to DataFrame
        outdir: Output directory
        timestamp: Timestamp string for filename
    """
    outdir.mkdir(parents=True, exist_ok=True)
    
    for symbol, df in data.items():
        filename = f"{symbol}_{timestamp}.json"
        filepath = outdir / filename
        
        # Convert DataFrame to JSON (orient='records' for row-based format)
        json_data = df.to_json(orient='records', date_format='iso', indent=2)
        
        filepath.write_text(json_data)
        LOG.info(f"Saved {len(df)} rows to {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="EGXpy Streaming Consumer - Fetch Egyptian Exchange market data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Daily data, last 10 bars
  python consumer.py --symbols COMI,ETEL --interval Daily --n-bars 10

  # Continuous polling (every 60 seconds)
  python consumer.py --symbols COMI --interval Daily --n-bars 5 --poll-interval 60

  # Intraday 5-minute data
  python consumer.py --symbols COMI,ETEL --interval "5 Minute" --start-date 2025-01-20 --end-date 2025-01-20

Popular Egyptian Stock Symbols:
  COMI - Commercial International Bank
  ETEL - Egyptian Company for Mobile Services (Etisalat)
  HELI - Heliopolis Housing
  SWDY - El Sewedy Electric
  OCDI - Orascom Construction
        """
    )
    
    parser.add_argument(
        "--symbols",
        required=True,
        help="Comma-separated list of stock symbols (e.g., COMI,ETEL)"
    )
    
    parser.add_argument(
        "--exchange",
        default="EGX",
        help="Exchange name (default: EGX)"
    )
    
    parser.add_argument(
        "--interval",
        default="Daily",
        choices=["Daily", "Weekly", "Monthly", "1 Minute", "5 Minute", "30 Minute"],
        help="Data interval (default: Daily)"
    )
    
    parser.add_argument(
        "--n-bars",
        type=int,
        default=10,
        help="Number of recent bars to fetch (for Daily/Weekly/Monthly, default: 10)"
    )
    
    parser.add_argument(
        "--start-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        help="Start date for intraday data (YYYY-MM-DD, required for intraday intervals)"
    )
    
    parser.add_argument(
        "--end-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        help="End date for intraday data (YYYY-MM-DD, required for intraday intervals)"
    )
    
    parser.add_argument(
        "--poll-interval",
        type=int,
        help="If set, continuously poll every N seconds (streaming mode)"
    )
    
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("extract/egxpy_streaming/raw"),
        help="Output directory for JSON files (default: extract/egxpy_streaming/raw)"
    )
    
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Parse symbols
    symbols = [s.strip() for s in args.symbols.split(",")]
    LOG.info(f"Starting EGXpy consumer for symbols: {symbols}")
    
    # Determine mode (daily vs intraday)
    is_intraday = args.interval in ["1 Minute", "5 Minute", "30 Minute"]
    
    if is_intraday:
        # Validate date range for intraday
        if not args.start_date or not args.end_date:
            LOG.error("--start-date and --end-date are required for intraday intervals")
            sys.exit(1)
        
        LOG.info(f"Mode: Intraday ({args.interval}) from {args.start_date} to {args.end_date}")
    else:
        LOG.info(f"Mode: {args.interval} (last {args.n_bars} bars)")
    
    # Fetch data (once or continuously)
    iteration = 0
    while True:
        iteration += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        LOG.info(f"=== Iteration {iteration} at {timestamp} ===")
        
        try:
            if is_intraday:
                data = fetch_intraday_data(symbols, args.interval, args.start_date, args.end_date)
            else:
                data = fetch_daily_data(symbols, args.exchange, args.interval, args.n_bars)
            
            if data:
                save_data(data, args.outdir, timestamp)
                LOG.info(f"Iteration {iteration} completed successfully")
            else:
                LOG.warning(f"No data fetched in iteration {iteration}")
                
        except KeyboardInterrupt:
            LOG.info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            LOG.error(f"Error in iteration {iteration}: {e}", exc_info=True)
        
        # Exit if not in polling mode
        if not args.poll_interval:
            LOG.info("Single fetch completed, exiting")
            break
        
        # Wait before next poll
        LOG.info(f"Waiting {args.poll_interval} seconds before next poll...")
        time.sleep(args.poll_interval)
    
    LOG.info("Consumer shutdown complete")


if __name__ == "__main__":
    main()
