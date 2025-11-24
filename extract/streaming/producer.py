#!/usr/bin/env python3
"""
Simple Kafka producer simulator for EGX ticks.

Usage:
  .venv/bin/python extract/streaming/producer.py --topic egx_ticks --count 100 --interval 0.5

Requirements:
  pip install kafka-python

This sends JSON messages with fields: symbol, timestamp, price, volume
"""

import argparse
import json
import random
import time
from datetime import datetime

from kafka import KafkaProducer


def make_message(symbol: str) -> dict:
    now = datetime.utcnow().isoformat()
    price = round(random.uniform(10, 200), 2)
    volume = random.randint(100, 10000)
    return {"symbol": symbol, "timestamp": now, "price": price, "volume": volume}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", default="localhost:9092", help="Kafka bootstrap servers")
    parser.add_argument("--topic", default="egx_ticks", help="Kafka topic to publish to")
    parser.add_argument("--symbol", default="COMI", help="Symbol to simulate")
    parser.add_argument("--count", type=int, default=10, help="Number of messages to send")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between messages")
    args = parser.parse_args()

    producer = KafkaProducer(bootstrap_servers=[args.bootstrap], value_serializer=lambda v: json.dumps(v).encode("utf-8"))

    print(f"Producing {args.count} messages to topic {args.topic}")
    for i in range(args.count):
        msg = make_message(args.symbol)
        producer.send(args.topic, msg)
        print("sent", msg)
        time.sleep(args.interval)

    producer.flush()
    print("Done")


if __name__ == "__main__":
    main()
