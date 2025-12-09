#!/usr/bin/env python3
"""
Kafka to Snowflake Consumer (Replaces consumer_influxdb.py)

Consumes streaming market data from Kafka and writes to Snowflake operational DB
using micro-batching for efficiency.

This replaces the InfluxDB consumer to create a unified data platform where
Grafana reads from Snowflake instead of InfluxDB.

Data Flow:
  EGX API → Kafka → Snowflake Operational → dbt → Snowflake DWH → Grafana

Usage:
    # Start consumer with default settings
    python consumer_snowflake.py --topic egx_market_data
    
    # Custom batch settings
    python consumer_snowflake.py --topic egx_market_data --batch-size 200 --batch-timeout 60

Environment Variables:
    KAFKA_BOOTSTRAP_SERVERS: Kafka brokers (default: localhost:9093)
    SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD
    SNOWFLAKE_DATABASE (default: EGX_OPERATIONAL)
    SNOWFLAKE_SCHEMA (default: RAW)
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import List, Dict, Any

from kafka import KafkaConsumer
from kafka.errors import KafkaError
import snowflake.connector
from snowflake.connector.errors import ProgrammingError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
LOG = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle SIGINT and SIGTERM for graceful shutdown"""
    global shutdown_requested
    LOG.info("Shutdown signal received. Finishing current batch...")
    shutdown_requested = True


def get_snowflake_connection():
    """Create Snowflake connection from environment variables"""
    required_vars = ['SNOWFLAKE_ACCOUNT', 'SNOWFLAKE_USER', 'SNOWFLAKE_PASSWORD']
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        raise ValueError(f"Missing required Snowflake credentials: {missing}")
    
    try:
        conn = snowflake.connector.connect(
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
            database=os.getenv('SNOWFLAKE_DATABASE', 'EGX_OPERATIONAL_DB'),
            schema=os.getenv('SNOWFLAKE_SCHEMA', 'OPERATIONAL'),
            role=os.getenv('SNOWFLAKE_ROLE', 'SYSADMIN')
        )
        LOG.info(f"Connected to Snowflake: {os.getenv('SNOWFLAKE_ACCOUNT')}")
        return conn
    except Exception as e:
        LOG.error(f"Failed to connect to Snowflake: {e}")
        raise


def create_kafka_consumer(bootstrap_servers: str, topic: str, group_id: str) -> KafkaConsumer:
    """Create Kafka consumer with JSON deserialization"""
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers.split(','),
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',  # Only process new messages
            enable_auto_commit=False,  # Manual commit after Snowflake write
            max_poll_records=500,
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000
        )
        LOG.info(f"Kafka consumer created: topic={topic}, group={group_id}")
        return consumer
    except Exception as e:
        LOG.error(f"Failed to create Kafka consumer: {e}")
        raise


def prepare_batch_insert_sql(table_name: str) -> str:
    """Generate parameterized INSERT statement for batch inserts matching TBL_STOCK_PRICE schema"""
    return f"""
        INSERT INTO {table_name} (
            COMPANY_ID, TRADE_DATE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, 
            CLOSE_PRICE, VOLUME, DATA_SOURCE, CREATED_AT
        ) 
        SELECT 
            c.COMPANY_ID, 
            %(trade_date)s, 
            %(open_price)s, 
            %(high_price)s, 
            %(low_price)s, 
            %(close_price)s, 
            %(volume)s, 
            %(data_source)s, 
            %(created_at)s
        FROM EGX_OPERATIONAL_DB.OPERATIONAL.TBL_COMPANY c
        WHERE c.SYMBOL = %(symbol)s
    """


def transform_message_to_record(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform Kafka message to TBL_STOCK_PRICE format
    
    Input (from egxpy producer):
        {
            'symbol': 'COMI',
            'datetime': '2025-12-08T14:30:00',
            'open': 10.5,
            'high': 10.8,
            'low': 10.4,
            'close': 10.7,
            'volume': 1000000,
            'interval': 'Daily',
            'exchange': 'EGX',
            'ingestion_timestamp': '2025-12-08T14:30:05'
        }
    
    Output (TBL_STOCK_PRICE columns):
        COMPANY_ID (looked up via JOIN), TRADE_DATE, OPEN_PRICE, HIGH_PRICE, 
        LOW_PRICE, CLOSE_PRICE, VOLUME, DATA_SOURCE, CREATED_AT
    """
    try:
        # Parse datetime to date only
        trade_datetime_str = message.get('datetime', '')
        try:
            trade_date = datetime.fromisoformat(trade_datetime_str.replace('Z', '+00:00')).date()
        except:
            trade_date = datetime.utcnow().date()
        
        return {
            'symbol': message.get('symbol', 'UNKNOWN'),
            'trade_date': trade_date,
            'open_price': float(message.get('open', 0)),
            'high_price': float(message.get('high', 0)),
            'low_price': float(message.get('low', 0)),
            'close_price': float(message.get('close', 0)),
            'volume': int(message.get('volume', 0)),
            'data_source': 'STREAMING_API',
            'created_at': datetime.utcnow()
        }
    except Exception as e:
        LOG.error(f"Failed to transform message: {e}, message: {message}")
        return None


def write_batch_to_snowflake(conn, records: List[Dict[str, Any]], table_name: str = 'EGX_OPERATIONAL_DB.OPERATIONAL.TBL_STOCK_PRICE') -> bool:
    """
    Write batch of records to Snowflake TBL_STOCK_PRICE
    
    First looks up COMPANY_ID for each symbol, then inserts with VALUES
    
    Returns:
        True if successful, False otherwise
    """
    if not records:
        return True
    
    cursor = conn.cursor()
    try:
        # Get unique symbols from batch
        symbols = list(set(r['symbol'] for r in records))
        symbol_placeholders = ','.join(['%s'] * len(symbols))
        
        # Lookup COMPANY_IDs for all symbols in batch
        lookup_sql = f"SELECT SYMBOL, COMPANY_ID FROM EGX_OPERATIONAL_DB.OPERATIONAL.TBL_COMPANY WHERE SYMBOL IN ({symbol_placeholders})"
        cursor.execute(lookup_sql, symbols)
        symbol_to_id = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Prepare INSERT statement
        insert_sql = f"""
            INSERT INTO {table_name} (
                COMPANY_ID, TRADE_DATE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, 
                CLOSE_PRICE, VOLUME, DATA_SOURCE, CREATED_AT
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """
        
        # Transform records to tuples with COMPANY_ID
        insert_data = []
        for record in records:
            symbol = record['symbol']
            if symbol not in symbol_to_id:
                LOG.warning(f"Symbol {symbol} not found in TBL_COMPANY, skipping")
                continue
            
            insert_data.append((
                symbol_to_id[symbol],
                record['trade_date'],
                record['open_price'],
                record['high_price'],
                record['low_price'],
                record['close_price'],
                record['volume'],
                record['data_source'],
                record['created_at']
            ))
        
        # Insert all records
        if insert_data:
            cursor.executemany(insert_sql, insert_data)
            conn.commit()
            LOG.info(f"✓ Inserted batch of {len(insert_data)} records to {table_name}")
        else:
            LOG.warning("No valid records to insert")
        
        return True
    except ProgrammingError as e:
        LOG.error(f"Snowflake insert failed: {e}")
        LOG.error(f"Sample record: {records[0] if records else 'No records'}")
        conn.rollback()
        return False
    except Exception as e:
        LOG.error(f"Unexpected error writing to Snowflake: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()


def consume_and_write(
    consumer: KafkaConsumer,
    conn,
    batch_size: int = 100,
    batch_timeout_seconds: int = 30
):
    """
    Main consumer loop: consume messages, batch, and write to Snowflake
    
    Args:
        consumer: Kafka consumer
        conn: Snowflake connection
        batch_size: Max records per batch
        batch_timeout_seconds: Max seconds to wait before flushing batch
    """
    batch = []
    last_flush_time = time.time()
    message_count = 0
    error_count = 0
    
    LOG.info("Starting consumer loop...")
    LOG.info(f"Batch settings: size={batch_size}, timeout={batch_timeout_seconds}s")
    
    try:
        for message in consumer:
            if shutdown_requested:
                LOG.info("Shutdown requested, flushing final batch...")
                break
            
            try:
                # Transform message
                record = transform_message_to_record(message.value)
                
                if record:
                    batch.append(record)
                    message_count += 1
                    
                    # Log sample
                    if message_count % 100 == 0:
                        LOG.info(f"Processed {message_count} messages, current batch: {len(batch)}")
                
                # Check if batch should be flushed
                time_since_flush = time.time() - last_flush_time
                should_flush = (
                    len(batch) >= batch_size or 
                    time_since_flush >= batch_timeout_seconds
                )
                
                if should_flush and batch:
                    # Write batch to Snowflake
                    success = write_batch_to_snowflake(conn, batch)
                    
                    if success:
                        # Commit Kafka offsets only after successful Snowflake write
                        consumer.commit()
                        LOG.debug(f"Committed Kafka offsets after {len(batch)} records")
                        batch = []
                        last_flush_time = time.time()
                    else:
                        error_count += 1
                        LOG.error(f"Failed to write batch (error #{error_count})")
                        
                        # On repeated failures, skip batch to avoid blocking
                        if error_count >= 3:
                            LOG.warning(f"Skipping batch of {len(batch)} records after {error_count} failures")
                            batch = []
                            error_count = 0
                            consumer.commit()
            
            except Exception as e:
                LOG.error(f"Error processing message: {e}", exc_info=True)
                continue
        
        # Flush any remaining records
        if batch:
            LOG.info(f"Flushing final batch of {len(batch)} records...")
            write_batch_to_snowflake(conn, batch)
            consumer.commit()
    
    except KeyboardInterrupt:
        LOG.info("Interrupted by user")
    except Exception as e:
        LOG.error(f"Consumer loop error: {e}", exc_info=True)
    finally:
        LOG.info(f"Consumer shutting down. Total messages processed: {message_count}")
        consumer.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Kafka to Snowflake consumer for real-time EGX market data"
    )
    
    parser.add_argument(
        '--topic',
        default='egx_market_data',
        help='Kafka topic to consume (default: egx_market_data)'
    )
    parser.add_argument(
        '--bootstrap',
        default=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9093'),
        help='Kafka bootstrap servers (default: localhost:9093)'
    )
    parser.add_argument(
        '--group-id',
        default='snowflake_consumer',
        help='Kafka consumer group ID (default: snowflake_consumer)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Max records per Snowflake batch (default: 100)'
    )
    parser.add_argument(
        '--batch-timeout',
        type=int,
        default=30,
        help='Max seconds before flushing batch (default: 30)'
    )
    parser.add_argument(
        '--table',
        default='STOCK_PRICES',
        help='Snowflake table name (default: STOCK_PRICES)'
    )
    
    args = parser.parse_args()
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Connect to Snowflake
        LOG.info("Connecting to Snowflake...")
        conn = get_snowflake_connection()
        
        # Create Kafka consumer
        LOG.info("Creating Kafka consumer...")
        consumer = create_kafka_consumer(args.bootstrap, args.topic, args.group_id)
        
        # Start consuming
        consume_and_write(
            consumer,
            conn,
            batch_size=args.batch_size,
            batch_timeout_seconds=args.batch_timeout
        )
        
    except Exception as e:
        LOG.error(f"Consumer failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
