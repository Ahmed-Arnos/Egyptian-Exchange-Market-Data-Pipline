#!/usr/bin/env python3
"""
Kafka consumer that writes incoming messages to MinIO (S3-compatible) under `streaming/` prefix.

Usage:
  .venv/bin/python extract/streaming/consumer_kafka.py --topic egx_ticks --bucket egx-bucket

Requirements:
  pip install kafka-python boto3

Environment variables for MinIO (example):
  export AWS_ACCESS_KEY_ID=minioadmin
  export AWS_SECRET_ACCESS_KEY=minioadmin
  export AWS_REGION=us-east-1
  export MINIO_ENDPOINT=http://localhost:9000

The script will create the bucket if it doesn't exist.
"""

import argparse
import json
import os
from datetime import datetime
from kafka import KafkaConsumer
import boto3
from botocore.client import Config


def make_s3_client(endpoint_url: str):
    session = boto3.session.Session()
    s3 = session.client('s3', endpoint_url=endpoint_url,
                        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                        config=Config(signature_version='s3v4'))
    return s3


def ensure_bucket(s3, bucket: str):
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception:
        print(f"Creating bucket {bucket}")
        s3.create_bucket(Bucket=bucket)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", default="localhost:9092")
    parser.add_argument("--topic", default="egx_ticks")
    parser.add_argument("--bucket", default="egx-bucket")
    parser.add_argument("--prefix", default="streaming/")
    parser.add_argument("--minio-endpoint", default=os.environ.get('MINIO_ENDPOINT', 'http://localhost:9000'))
    args = parser.parse_args()

    consumer = KafkaConsumer(args.topic, bootstrap_servers=[args.bootstrap], auto_offset_reset='earliest', value_deserializer=lambda m: json.loads(m.decode('utf-8')))

    s3 = make_s3_client(args.minio_endpoint)
    ensure_bucket(s3, args.bucket)

    print(f"Listening to {args.topic}, writing to s3://{args.bucket}/{args.prefix}")
    for msg in consumer:
        value = msg.value
        symbol = value.get('symbol', 'unknown')
        ts = value.get('timestamp') or datetime.utcnow().isoformat()
        key = f"{args.prefix}{symbol}/{ts}.json"
        s3.put_object(Bucket=args.bucket, Key=key, Body=json.dumps(value).encode('utf-8'))
        print("wrote", key)


if __name__ == '__main__':
    main()
