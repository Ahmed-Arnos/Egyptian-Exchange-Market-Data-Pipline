#!/usr/bin/env python3
"""
EODHD Historical Data Producer for Kafka

Fetches historical EOD data from EODHD API and publishes to Kafka topic.
Can be used to backfill historical data or validate against egxpy.

Data Flow:
  EODHD API → Kafka → Snowflake (via consumer_snowflake.py)

Usage:
    # Fetch last 30 days for 16 companies
    python producer_eodhd.py --symbols COMI,ETEL,SWDY --days 30
    
    # Fetch custom date range
    python producer_eodhd.py --symbols COMI --from 2024-01-01 --to 2025-12-08
    
    # Fetch all available EGX companies (use carefully - API limits!)
    python producer_eodhd.py --all-egx --days 7

Environment Variables:
    EODHD_API_KEY: API key (required)
    KAFKA_BOOTSTRAP_SERVERS: Kafka brokers (default: localhost:9093)
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import requests
from kafka import KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOG = logging.getLogger(__name__)

# EODHD Configuration
API_KEY = os.getenv('EODHD_API_KEY')
BASE_URL = "https://eodhd.com/api"
EXCHANGE = "EGX"  # Egyptian Exchange

# Default symbols (your 16 companies)
DEFAULT_SYMBOLS = [
    'COMI', 'ETEL', 'SWDY', 'PHDC', 'ORAS', 'ESRS', 'HRHO', 'OCDI',
    'SKPC', 'TMGH', 'JUFO', 'EKHO', 'CLHO', 'OTMT', 'BTFH', 'HELI'
]


def create_kafka_producer(bootstrap_servers: str) -> KafkaProducer:
    """Create Kafka producer with JSON serialization"""
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers.split(','),
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda k: k.encode('utf-8') if k else None,
        acks='all',
        retries=3,
        max_in_flight_requests_per_connection=1
    )


def get_all_egx_tickers() -> List[str]:
    """Fetch complete list of Egyptian Exchange tickers"""
    LOG.info("Fetching all EGX tickers...")
    url = f"{BASE_URL}/exchange-symbol-list/{EXCHANGE}"
    params = {'api_token': API_KEY, 'fmt': 'json'}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        tickers = response.json()
        symbols = [t['Code'] for t in tickers if t.get('Type') == 'Common Stock']
        
        LOG.info(f"✓ Found {len(symbols)} EGX common stocks")
        return symbols
    
    except requests.exceptions.RequestException as e:
        LOG.error(f"Failed to fetch EGX tickers: {e}")
        return []


def fetch_historical_eod(symbol: str, from_date: str, to_date: str) -> Optional[List[Dict]]:
    """
    Fetch historical End-of-Day data from EODHD
    
    Args:
        symbol: Stock symbol (e.g., 'COMI')
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
    
    Returns:
        List of OHLCV data dictionaries
    """
    ticker = f"{symbol}.{EXCHANGE}"
    url = f"{BASE_URL}/eod/{ticker}"
    params = {
        'api_token': API_KEY,
        'from': from_date,
        'to': to_date,
        'fmt': 'json'
    }
    
    try:
        LOG.info(f"Fetching {symbol} from {from_date} to {to_date}...")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data:
            LOG.warning(f"No data returned for {symbol}")
            return None
        
        LOG.info(f"✓ Retrieved {len(data)} bars for {symbol}")
        return data
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            LOG.warning(f"Symbol {symbol} not found on {EXCHANGE}")
        else:
            LOG.error(f"HTTP error fetching {symbol}: {e}")
        return None
    
    except requests.exceptions.RequestException as e:
        LOG.error(f"Failed to fetch {symbol}: {e}")
        return None


def transform_to_kafka_message(symbol: str, bar: Dict) -> Dict:
    """
    Transform EODHD bar data to Kafka message format
    
    EODHD format:
    {
        "date": "2025-12-07",
        "open": 116.8,
        "high": 117.9,
        "low": 115.9,
        "close": 116.2,
        "adjusted_close": 116.2,
        "volume": 882445
    }
    
    Kafka message format (compatible with egxpy messages):
    {
        "symbol": "COMI",
        "datetime": "2025-12-07T16:00:00",
        "open": 116.8,
        "high": 117.9,
        "low": 115.9,
        "close": 116.2,
        "volume": 882445,
        "interval": "Daily",
        "exchange": "EGX",
        "data_source": "EODHD",
        "ingestion_timestamp": "2025-12-08T10:30:00"
    }
    """
    return {
        'symbol': symbol,
        'datetime': f"{bar['date']}T16:00:00",  # Market close time (4 PM)
        'open': float(bar['open']),
        'high': float(bar['high']),
        'low': float(bar['low']),
        'close': float(bar['close']),
        'volume': int(bar['volume']),
        'adjusted_close': float(bar.get('adjusted_close', bar['close'])),
        'interval': 'Daily',
        'exchange': EXCHANGE,
        'data_source': 'EODHD',
        'ingestion_timestamp': datetime.utcnow().isoformat()
    }


def publish_to_kafka(
    producer: KafkaProducer,
    topic: str,
    symbol: str,
    bars: List[Dict]
) -> int:
    """
    Publish historical bars to Kafka
    
    Returns:
        Number of messages published
    """
    published = 0
    
    for bar in bars:
        try:
            message = transform_to_kafka_message(symbol, bar)
            
            # Use symbol as key for consistent partitioning
            future = producer.send(topic, key=symbol, value=message)
            
            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            published += 1
            
            if published % 100 == 0:
                LOG.debug(f"Published {published} messages for {symbol}")
        
        except KafkaError as e:
            LOG.error(f"Failed to publish {symbol} bar: {e}")
            continue
    
    producer.flush()
    LOG.info(f"✓ Published {published} messages for {symbol}")
    return published


def main():
    parser = argparse.ArgumentParser(
        description="EODHD Historical Data Producer for Kafka"
    )
    
    parser.add_argument(
        '--symbols',
        help='Comma-separated list of symbols (e.g., COMI,ETEL,SWDY)'
    )
    parser.add_argument(
        '--all-egx',
        action='store_true',
        help='Fetch all EGX stocks (WARNING: uses many API calls!)'
    )
    parser.add_argument(
        '--from',
        dest='from_date',
        help='Start date (YYYY-MM-DD). Defaults to 30 days ago'
    )
    parser.add_argument(
        '--to',
        dest='to_date',
        default=datetime.now().strftime('%Y-%m-%d'),
        help='End date (YYYY-MM-DD). Defaults to today'
    )
    parser.add_argument(
        '--days',
        type=int,
        help='Fetch last N days (alternative to --from)'
    )
    parser.add_argument(
        '--topic',
        default='egx_market_data',
        help='Kafka topic (default: egx_market_data)'
    )
    parser.add_argument(
        '--bootstrap',
        default=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9093'),
        help='Kafka bootstrap servers'
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=3.0,
        help='Delay between API calls in seconds (default: 3.0, free plan: 20 calls/day)'
    )
    
    args = parser.parse_args()
    
    # Determine date range
    if args.days:
        from_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    elif args.from_date:
        from_date = args.from_date
    else:
        from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    to_date = args.to_date
    
    # Determine symbols
    if args.all_egx:
        symbols = get_all_egx_tickers()
        if not symbols:
            LOG.error("Failed to fetch EGX ticker list")
            sys.exit(1)
        
        LOG.warning(f"⚠️  Fetching {len(symbols)} symbols will use {len(symbols)} API calls!")
        LOG.warning(f"⚠️  Free plan limit: 20 calls/day. Consider using --symbols instead.")
        
        confirm = input("Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            LOG.info("Aborted by user")
            sys.exit(0)
    
    elif args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    else:
        symbols = DEFAULT_SYMBOLS
        LOG.info(f"Using default 16 symbols: {', '.join(symbols)}")
    
    LOG.info(f"Date range: {from_date} to {to_date}")
    LOG.info(f"Symbols to fetch: {len(symbols)}")
    LOG.info(f"Rate limit: {args.rate_limit}s between calls")
    
    # Create Kafka producer
    try:
        producer = create_kafka_producer(args.bootstrap)
        LOG.info(f"✓ Connected to Kafka: {args.bootstrap}")
    except Exception as e:
        LOG.error(f"Failed to connect to Kafka: {e}")
        sys.exit(1)
    
    # Fetch and publish data
    total_published = 0
    total_api_calls = 0
    
    for i, symbol in enumerate(symbols, 1):
        LOG.info(f"[{i}/{len(symbols)}] Processing {symbol}...")
        
        # Fetch historical data
        bars = fetch_historical_eod(symbol, from_date, to_date)
        total_api_calls += 1
        
        if bars:
            # Publish to Kafka
            published = publish_to_kafka(producer, args.topic, symbol, bars)
            total_published += published
        
        # Rate limiting (important for free plan!)
        if i < len(symbols):
            LOG.debug(f"Rate limiting: sleeping {args.rate_limit}s...")
            time.sleep(args.rate_limit)
    
    producer.close()
    
    # Summary
    LOG.info("=" * 80)
    LOG.info("SUMMARY")
    LOG.info("=" * 80)
    LOG.info(f"Symbols processed:   {len(symbols)}")
    LOG.info(f"API calls made:      {total_api_calls}")
    LOG.info(f"Messages published:  {total_published}")
    LOG.info(f"Topic:               {args.topic}")
    LOG.info("=" * 80)
    LOG.info("✓ Producer completed successfully")
    
    # API limit warning
    if total_api_calls >= 15:
        LOG.warning("⚠️  You've used 15+ API calls. Free plan limit: 20/day")
        LOG.warning("⚠️  Consider spacing out requests or upgrading plan")


if __name__ == '__main__':
    main()
