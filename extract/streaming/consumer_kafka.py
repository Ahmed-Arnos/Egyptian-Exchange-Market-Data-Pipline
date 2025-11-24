#!/usr/bin/env python3
"""
Kafka consumer for EGX market data that writes to S3/MinIO with proper partitioning.

Consumes messages from Kafka topic (published by egxpy producer) and writes to S3
with date/symbol partitioning for efficient querying:
  s3://bucket/streaming/date=YYYY-MM-DD/symbol=XXXX/HHMMSSffffff.json

Usage:
  # Local MinIO
  python consumer_kafka.py --topic egx_market_data --bucket egx-data-bucket --minio-endpoint http://localhost:9000

  # AWS S3 (production)
  python consumer_kafka.py --topic egx_market_data --bucket egx-data-bucket --use-aws

Environment variables:
  AWS_ACCESS_KEY_ID: S3/MinIO access key
  AWS_SECRET_ACCESS_KEY: S3/MinIO secret key
  AWS_REGION: AWS region (default: us-east-1)
  MINIO_ENDPOINT: MinIO endpoint for local dev (default: http://localhost:9000)
  KAFKA_BOOTSTRAP_SERVERS: Kafka brokers (default: localhost:9092)
"""

import argparse
import json
import logging
import os
from datetime import datetime
from kafka import KafkaConsumer
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

LOG = logging.getLogger(__name__)


def make_s3_client(endpoint_url: str = None, use_aws: bool = False):
    """Create S3 client for MinIO or AWS."""
    session = boto3.session.Session()
    
    if use_aws:
        # Use AWS S3 (no endpoint_url)
        s3 = session.client('s3',
                           aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                           aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                           region_name=os.environ.get('AWS_REGION', 'us-east-1'))
    else:
        # Use MinIO (local dev)
        s3 = session.client('s3', 
                           endpoint_url=endpoint_url,
                           aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID', 'minioadmin'),
                           aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY', 'minioadmin'),
                           config=Config(signature_version='s3v4'))
    
    return s3


def ensure_bucket(s3, bucket: str):
    """Create bucket if it doesn't exist."""
    try:
        s3.head_bucket(Bucket=bucket)
        LOG.info(f"Bucket {bucket} exists")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            LOG.info(f"Creating bucket {bucket}")
            try:
                s3.create_bucket(Bucket=bucket)
            except ClientError as create_error:
                LOG.warning(f"Could not create bucket: {create_error}")
        else:
            LOG.error(f"Error checking bucket: {e}")


def build_s3_key(prefix: str, message: dict) -> str:
    """
    Build S3 key with date/symbol partitioning.
    
    Format: streaming/date=YYYY-MM-DD/symbol=XXXX/HHMMSSffffff.json
    
    Args:
        prefix: Base prefix (e.g., 'streaming/')
        message: Message dict with 'symbol' and 'datetime' fields
    
    Returns:
        S3 object key
    """
    symbol = message.get('symbol', 'unknown')
    
    # Parse datetime from message or use current time
    msg_datetime = message.get('datetime')
    if msg_datetime:
        try:
            dt = datetime.fromisoformat(msg_datetime.replace('Z', '+00:00'))
        except:
            dt = datetime.utcnow()
    else:
        dt = datetime.utcnow()
    
    # Build partitioned key
    date_str = dt.strftime('%Y-%m-%d')
    time_str = dt.strftime('%H%M%S%f')  # HHMMSSffffff for uniqueness
    
    key = f"{prefix}date={date_str}/symbol={symbol}/{time_str}.json"
    return key


def main():
    parser = argparse.ArgumentParser(
        description="Kafka consumer for EGX market data → S3/MinIO",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--bootstrap",
        default=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        help="Kafka bootstrap servers (default: localhost:9092)"
    )
    
    parser.add_argument(
        "--topic",
        default="egx_market_data",
        help="Kafka topic to consume (default: egx_market_data)"
    )
    
    parser.add_argument(
        "--bucket",
        default="egx-data-bucket",
        help="S3/MinIO bucket name (default: egx-data-bucket)"
    )
    
    parser.add_argument(
        "--prefix",
        default="streaming/",
        help="S3 key prefix (default: streaming/)"
    )
    
    parser.add_argument(
        "--minio-endpoint",
        default=os.environ.get('MINIO_ENDPOINT', 'http://localhost:9000'),
        help="MinIO endpoint for local dev (default: http://localhost:9000)"
    )
    
    parser.add_argument(
        "--use-aws",
        action='store_true',
        help="Use AWS S3 instead of MinIO (for production)"
    )
    
    parser.add_argument(
        "--consumer-group",
        default="egx-s3-writer",
        help="Kafka consumer group ID (default: egx-s3-writer)"
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
    
    LOG.info(f"Starting Kafka consumer for topic: {args.topic}")
    LOG.info(f"Writing to: s3://{args.bucket}/{args.prefix}")
    LOG.info(f"Storage backend: {'AWS S3' if args.use_aws else 'MinIO'}")
    
    # Create Kafka consumer
    consumer = KafkaConsumer(
        args.topic,
        bootstrap_servers=args.bootstrap.split(','),
        group_id=args.consumer_group,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    # Create S3 client
    s3 = make_s3_client(
        endpoint_url=args.minio_endpoint if not args.use_aws else None,
        use_aws=args.use_aws
    )
    ensure_bucket(s3, args.bucket)
    
    LOG.info("Consumer ready, waiting for messages...")
    
    message_count = 0
    try:
        for msg in consumer:
            message_count += 1
            value = msg.value
            
            # Build partitioned S3 key
            key = build_s3_key(args.prefix, value)
            
            # Write to S3
            try:
                s3.put_object(
                    Bucket=args.bucket,
                    Key=key,
                    Body=json.dumps(value, indent=2).encode('utf-8'),
                    ContentType='application/json'
                )
                LOG.info(f"[{message_count}] Wrote {key}")
            except ClientError as e:
                LOG.error(f"Failed to write {key}: {e}")
    
    except KeyboardInterrupt:
        LOG.info("Received interrupt signal, shutting down...")
    finally:
        consumer.close()
        LOG.info(f"Consumer shutdown complete. Processed {message_count} messages.")


if __name__ == '__main__':
    main()
