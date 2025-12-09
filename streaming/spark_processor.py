from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def write_to_influxdb(batch_df, batch_id):
    """
    Write batch to InfluxDB using the Python client.
    """
    try:
        # Collect data to driver (okay for small batches)
        records = batch_df.collect()
        
        if not records:
            return

        from influxdb_client import InfluxDBClient, Point
        from influxdb_client.client.write_api import SYNCHRONOUS

        # InfluxDB Settings (match docker-compose)
        url = "http://influxdb:8086"
        token = "egx-market-data-token-2025"
        org = "egx"
        bucket = "market_data"

        client = InfluxDBClient(url=url, token=token, org=org)
        write_api = client.write_api(write_options=SYNCHRONOUS)

        points = []
        for row in records:
            # Create Point
            # Measurement: stock_price
            # Tags: symbol, exchange, interval
            # Fields: open, high, low, close, volume
            # Time: datetime
            
            p = Point("stock_price") \
                .tag("symbol", row.symbol) \
                .tag("exchange", row.exchange) \
                .tag("interval", row.interval) \
                .field("open", float(row.open)) \
                .field("high", float(row.high)) \
                .field("low", float(row.low)) \
                .field("close", float(row.close)) \
                .field("volume", int(row.volume)) \
                .time(row.datetime)
            
            points.append(p)

        write_api.write(bucket=bucket, org=org, record=points)
        logger.info(f"Batch {batch_id}: Wrote {len(points)} records to InfluxDB")
        client.close()

    except Exception as e:
        logger.error(f"Error writing to InfluxDB: {e}")

def main():
    spark = SparkSession.builder \
        .appName("EGXStreamingProcessor") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    # Define Schema (matches producer JSON)
    schema = StructType([
        StructField("symbol", StringType()),
        StructField("exchange", StringType()),
        StructField("interval", StringType()),
        StructField("datetime", StringType()), # ISO string
        StructField("open", DoubleType()),
        StructField("high", DoubleType()),
        StructField("low", DoubleType()),
        StructField("close", DoubleType()),
        StructField("volume", IntegerType()),
        StructField("ingestion_timestamp", StringType())
    ])

    # Read from Kafka
    # Use docker-kafka-1 as the host since that's the actual container name
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "docker-kafka-1:9093") \
        .option("subscribe", "egx_market_data") \
        .option("startingOffsets", "latest") \
        .load()

    # Parse JSON
    parsed_df = df.select(from_json(col("value").cast("string"), schema).alias("data")).select("data.*")

    # Write to InfluxDB
    query = parsed_df.writeStream \
        .foreachBatch(write_to_influxdb) \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    main()
