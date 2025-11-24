#!/usr/bin/env python3
"""
EGXpy Kafka Producer

Fetches Egyptian Exchange (EGX) market data using egxpy and publishes to Kafka.
Replaces the direct-to-disk consumer with a streaming architecture:
  EGX API → egxpy → Kafka → S3/MinIO

Usage:
    # Publish daily data to Kafka (continuous polling)
    python producer_kafka.py --symbols COMI,ETEL --interval Daily --n-bars 10 --poll-interval 60

    # Publish intraday data once
    python producer_kafka.py --symbols COMI --interval "5 Minute" --start-date 2025-01-20 --end-date 2025-01-20

Environment Variables:
    KAFKA_BOOTSTRAP_SERVERS: Kafka broker(s) (default: localhost:9092)
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import date, datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError

from egxpy.download import get_OHLCV_data, get_EGX_intraday_data

LOG = logging.getLogger(__name__)


def create_kafka_producer(bootstrap_servers: str) -> KafkaProducer:
    """Create and return a Kafka producer with JSON serialization."""
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers.split(','),
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda k: k.encode('utf-8') if k else None,
        acks='all',  # Wait for all replicas
        retries=3,
        max_in_flight_requests_per_connection=1  # Ensure ordering
    )


def publish_daily_data(producer: KafkaProducer, topic: str, symbols: list[str], 
                       exchange: str, interval: str, n_bars: int) -> int:
    """
    Fetch daily OHLCV data and publish each row to Kafka.
    
    Returns:
        Number of messages published
    """
    published = 0
    
    for symbol in symbols:
        try:
            LOG.info(f"Fetching {interval} data for {symbol} (last {n_bars} bars)...")
            df = get_OHLCV_data(symbol, exchange, interval, n_bars)
            
            if df.empty:
                LOG.warning(f"No data returned for {symbol}")
                continue
            
            LOG.info(f"Retrieved {len(df)} rows for {symbol}")
            
            # Publish each bar as a separate message
            for idx, row in df.iterrows():
                message = {
                    'symbol': symbol,
                    'exchange': exchange,
                    'interval': interval,
                    'datetime': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                    'open': float(row.get('open', 0)),
                    'high': float(row.get('high', 0)),
                    'low': float(row.get('low', 0)),
                    'close': float(row.get('close', 0)),
                    'volume': int(row.get('volume', 0)),
                    'ingestion_timestamp': datetime.utcnow().isoformat()
                }
                
                # Use symbol as message key for partitioning
                future = producer.send(topic, key=symbol, value=message)
                
                try:
                    record_metadata = future.get(timeout=10)
                    LOG.debug(f"Published {symbol} bar to partition {record_metadata.partition} offset {record_metadata.offset}")
                    published += 1
                except KafkaError as e:
                    LOG.error(f"Failed to publish {symbol} bar: {e}")
            
            LOG.info(f"Published {published} messages for {symbol}")
                    
        except Exception as e:
            LOG.error(f"Failed to fetch/publish {symbol}: {e}", exc_info=True)
    
    return published


def publish_intraday_data(producer: KafkaProducer, topic: str, symbols: list[str],
                          interval: str, start_date: date, end_date: date) -> int:
    """
    Fetch intraday data and publish to Kafka.
    
    Returns:
        Number of messages published
    """
    published = 0
    
    try:
        LOG.info(f"Fetching {interval} intraday data for {symbols} from {start_date} to {end_date}...")
        df = get_EGX_intraday_data(symbols, interval, start_date, end_date)
        
        if df.empty:
            LOG.warning("No intraday data returned")
            return 0
        
        LOG.info(f"Retrieved {len(df)} rows with columns: {df.columns.tolist()}")
        
        # Publish each row
        for idx, row in df.iterrows():
            # Extract symbol from column name (format: 'SYMBOL_field')
            for col in df.columns:
                if '_' in col:
                    symbol_part = col.split('_')[0]
                    if symbol_part in symbols:
                        message = {
                            'symbol': symbol_part,
                            'interval': interval,
                            'datetime': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                            'value': float(row[col]) if row[col] is not None else None,
                            'field': col.split('_', 1)[1] if '_' in col else 'value',
                            'ingestion_timestamp': datetime.utcnow().isoformat()
                        }
                        
                        future = producer.send(topic, key=symbol_part, value=message)
                        future.get(timeout=10)
                        published += 1
        
        LOG.info(f"Published {published} intraday messages")
        
    except Exception as e:
        LOG.error(f"Failed to fetch/publish intraday data: {e}", exc_info=True)
    
    return published


def main():
    parser = argparse.ArgumentParser(
        description="EGXpy Kafka Producer - Fetch EGX data and publish to Kafka",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Daily data, publish once
  python producer_kafka.py --symbols COMI,ETEL --interval Daily --n-bars 10

  # Continuous polling (every 60 seconds)
  python producer_kafka.py --symbols COMI --interval Daily --n-bars 5 --poll-interval 60

  # Intraday 5-minute data
  python producer_kafka.py --symbols COMI,ETEL --interval "5 Minute" --start-date 2025-01-20 --end-date 2025-01-20
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
        help="Start date for intraday data (YYYY-MM-DD, required for intraday)"
    )
    
    parser.add_argument(
        "--end-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        help="End date for intraday data (YYYY-MM-DD, required for intraday)"
    )
    
    parser.add_argument(
        "--poll-interval",
        type=int,
        help="If set, continuously poll every N seconds (streaming mode)"
    )
    
    parser.add_argument(
        "--topic",
        default="egx_market_data",
        help="Kafka topic name (default: egx_market_data)"
    )
    
    parser.add_argument(
        "--bootstrap-servers",
        default=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        help="Kafka bootstrap servers (default: localhost:9092)"
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
    LOG.info(f"Starting EGXpy Kafka producer for symbols: {symbols}")
    LOG.info(f"Kafka topic: {args.topic}, bootstrap servers: {args.bootstrap_servers}")
    
    # Create Kafka producer
    try:
        producer = create_kafka_producer(args.bootstrap_servers)
        LOG.info("Kafka producer connected successfully")
    except Exception as e:
        LOG.error(f"Failed to connect to Kafka: {e}")
        sys.exit(1)
    
    # Determine mode
    is_intraday = args.interval in ["1 Minute", "5 Minute", "30 Minute"]
    
    if is_intraday and (not args.start_date or not args.end_date):
        LOG.error("--start-date and --end-date are required for intraday intervals")
        sys.exit(1)
    
    # Publish data (once or continuously)
    iteration = 0
    try:
        while True:
            iteration += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            LOG.info(f"=== Iteration {iteration} at {timestamp} ===")
            
            try:
                if is_intraday:
                    published = publish_intraday_data(producer, args.topic, symbols, 
                                                     args.interval, args.start_date, args.end_date)
                else:
                    published = publish_daily_data(producer, args.topic, symbols, 
                                                  args.exchange, args.interval, args.n_bars)
                
                LOG.info(f"Iteration {iteration} completed: {published} messages published")
                
            except Exception as e:
                LOG.error(f"Error in iteration {iteration}: {e}", exc_info=True)
            
            # Exit if not in polling mode
            if not args.poll_interval:
                LOG.info("Single fetch completed, exiting")
                break
            
            # Wait before next poll
            LOG.info(f"Waiting {args.poll_interval} seconds before next poll...")
            time.sleep(args.poll_interval)
    
    except KeyboardInterrupt:
        LOG.info("Received interrupt signal, shutting down...")
    finally:
        producer.flush()
        producer.close()
        LOG.info("Producer shutdown complete")


if __name__ == "__main__":
    main()
