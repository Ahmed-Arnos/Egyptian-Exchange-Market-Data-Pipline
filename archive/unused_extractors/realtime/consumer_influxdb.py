#!/usr/bin/env python3
"""
Real-time Kafka consumer for EGX market data that writes to InfluxDB.

This consumer is part of the streaming pipeline (not batch):
  Kafka → InfluxDB → Grafana (real-time visualization)

The batch pipeline (Kafka → S3) runs separately with consumer_kafka.py

Usage:
  # Local development (default)
  python consumer_influxdb.py --topic egx_market_data --bootstrap localhost:9093

  # Custom InfluxDB connection
  python consumer_influxdb.py --influxdb-url http://localhost:8086 --influxdb-token your-token

Environment Variables:
  KAFKA_BOOTSTRAP_SERVERS: Kafka brokers (default: localhost:9093)
  INFLUXDB_URL: InfluxDB server URL (default: http://localhost:8086)
  INFLUXDB_TOKEN: InfluxDB authentication token
  INFLUXDB_ORG: InfluxDB organization (default: egx)
  INFLUXDB_BUCKET: InfluxDB bucket name (default: market_data)
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

LOG = logging.getLogger(__name__)


def create_influxdb_client(url: str, token: str, org: str) -> InfluxDBClient:
    """Create and return an InfluxDB client."""
    try:
        client = InfluxDBClient(url=url, token=token, org=org)
        # Test connection
        health = client.health()
        LOG.info(f"InfluxDB connection successful: {health.status}")
        return client
    except Exception as e:
        LOG.error(f"Failed to connect to InfluxDB: {e}")
        raise


def write_to_influxdb(write_api, bucket: str, message: dict, message_count: int):
    """
    Write stock market data to InfluxDB.
    
    Data structure in InfluxDB:
      measurement: stock_price
      tags: symbol, exchange, interval
      fields: open, high, low, close, volume
      timestamp: datetime from message
    """
    try:
        # Parse timestamp
        timestamp_str = message.get('datetime')
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()
        
        # Create point
        point = Point("stock_price") \
            .tag("symbol", message.get('symbol', 'UNKNOWN')) \
            .tag("exchange", message.get('exchange', 'EGX')) \
            .tag("interval", message.get('interval', 'Daily')) \
            .field("open", float(message.get('open', 0))) \
            .field("high", float(message.get('high', 0))) \
            .field("low", float(message.get('low', 0))) \
            .field("close", float(message.get('close', 0))) \
            .field("volume", int(message.get('volume', 0))) \
            .time(timestamp)
        
        # Write to InfluxDB
        write_api.write(bucket=bucket, record=point)
        LOG.info(f"[{message_count}] Wrote {message.get('symbol')} @ {timestamp.strftime('%Y-%m-%d %H:%M:%S')}: close={message.get('close')}")
        
    except Exception as e:
        LOG.error(f"Failed to write to InfluxDB: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Kafka to InfluxDB consumer for real-time EGX market data"
    )
    
    parser.add_argument(
        "--topic",
        default="egx_market_data",
        help="Kafka topic to consume from (default: egx_market_data)"
    )
    
    parser.add_argument(
        "--bootstrap",
        default=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9093'),
        help="Kafka bootstrap servers (default: localhost:9093)"
    )
    
    parser.add_argument(
        "--consumer-group",
        default="egx-influxdb-writer",
        help="Kafka consumer group ID (default: egx-influxdb-writer)"
    )
    
    parser.add_argument(
        "--influxdb-url",
        default=os.environ.get('INFLUXDB_URL', 'http://localhost:8086'),
        help="InfluxDB server URL (default: http://localhost:8086)"
    )
    
    parser.add_argument(
        "--influxdb-token",
        default=os.environ.get('INFLUXDB_TOKEN', 'egx-market-data-token-2025'),
        help="InfluxDB authentication token"
    )
    
    parser.add_argument(
        "--influxdb-org",
        default=os.environ.get('INFLUXDB_ORG', 'egx'),
        help="InfluxDB organization (default: egx)"
    )
    
    parser.add_argument(
        "--influxdb-bucket",
        default=os.environ.get('INFLUXDB_BUCKET', 'market_data'),
        help="InfluxDB bucket name (default: market_data)"
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
    
    LOG.info(f"Starting real-time Kafka → InfluxDB consumer")
    LOG.info(f"Kafka topic: {args.topic}")
    LOG.info(f"InfluxDB: {args.influxdb_url} (org: {args.influxdb_org}, bucket: {args.influxdb_bucket})")
    
    # Create InfluxDB client
    influxdb_client = create_influxdb_client(
        url=args.influxdb_url,
        token=args.influxdb_token,
        org=args.influxdb_org
    )
    write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
    
    # Create Kafka consumer
    consumer = KafkaConsumer(
        args.topic,
        bootstrap_servers=args.bootstrap.split(','),
        group_id=args.consumer_group,
        auto_offset_reset='latest',  # Only consume new messages (real-time)
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    LOG.info("Consumer ready, waiting for real-time messages...")
    
    message_count = 0
    try:
        for msg in consumer:
            message_count += 1
            value = msg.value
            write_to_influxdb(write_api, args.influxdb_bucket, value, message_count)
    
    except KeyboardInterrupt:
        LOG.info("Received interrupt signal, shutting down...")
    finally:
        consumer.close()
        influxdb_client.close()
        LOG.info(f"Consumer shutdown complete. Processed {message_count} messages.")


if __name__ == '__main__':
    main()
