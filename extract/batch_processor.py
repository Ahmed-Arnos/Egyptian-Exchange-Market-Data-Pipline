#!/usr/bin/env python3
"""
Batch Data Processor for Egyptian Exchange Pipeline
---------------------------------------------------
Processes CSV files from S3 and loads them into Snowflake OPERATIONAL tables.
Used by Airflow DAG for batch data ingestion.

Usage:
    python batch_processor.py [--bucket BUCKET] [--prefix PREFIX] [--since DAYS]
"""

import argparse
import boto3
import pandas as pd
import snowflake.connector
import os
from datetime import datetime, timedelta
from io import StringIO


def get_s3_client():
    """Create S3 client with AWS credentials"""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'us-east-1')
    )


def get_snowflake_connection():
    """Create Snowflake connection"""
    return snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
        database='EGX_OPERATIONAL_DB',
        schema='OPERATIONAL'
    )


def list_recent_files(s3_client, bucket_name, prefix, since_days):
    """List files in S3 modified in the last N days"""
    cutoff_date = datetime.now() - timedelta(days=since_days)
    
    print(f"Checking S3 bucket '{bucket_name}' for files in '{prefix}' modified since {cutoff_date}")
    
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        
        if 'Contents' not in response:
            print("No files found in S3")
            return []
        
        recent_files = []
        for obj in response['Contents']:
            if obj['LastModified'].replace(tzinfo=None) > cutoff_date:
                if obj['Key'].endswith('.csv'):
                    recent_files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'modified': obj['LastModified']
                    })
        
        print(f"Found {len(recent_files)} recent CSV files")
        return recent_files
    
    except Exception as e:
        print(f"Error listing S3 files: {e}")
        return []


def process_csv_file(s3_client, conn, bucket_name, file_key):
    """Process a single CSV file from S3 and load to Snowflake"""
    print(f"\nProcessing: {file_key}")
    
    try:
        # Download file from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        csv_content = response['Body'].read().decode('utf-8')
        
        # Read CSV into pandas DataFrame
        df = pd.read_csv(StringIO(csv_content))
        
        print(f"  Rows: {len(df)}, Columns: {list(df.columns)}")
        
        # Determine table based on file name/path
        if 'company' in file_key.lower() or 'list' in file_key.lower():
            table_name = 'TBL_COMPANY'
            load_company_data(conn, df)
        elif 'price' in file_key.lower() or 'ohlc' in file_key.lower():
            table_name = 'TBL_STOCK_PRICE'
            load_price_data(conn, df)
        elif 'financial' in file_key.lower():
            table_name = 'TBL_FINANCIAL'
            load_financial_data(conn, df)
        else:
            print(f"  ⚠ Unknown file type, skipping")
            return False
        
        print(f"  ✓ Loaded {len(df)} records to {table_name}")
        return True
    
    except Exception as e:
        print(f"  ✗ Error processing file: {e}")
        return False


def load_company_data(conn, df):
    """Load company data to TBL_COMPANY"""
    cursor = conn.cursor()
    
    # Expected columns: symbol, company_name, sector, market_cap
    required_cols = ['symbol', 'company_name']
    if not all(col in df.columns for col in required_cols):
        print(f"  ⚠ Missing required columns. Found: {list(df.columns)}")
        return
    
    # Add optional columns with defaults
    if 'sector' not in df.columns:
        df['sector'] = 'Unknown'
    if 'market_cap' not in df.columns:
        df['market_cap'] = 0
    
    # Insert or update companies
    for _, row in df.iterrows():
        cursor.execute("""
            MERGE INTO TBL_COMPANY AS target
            USING (SELECT %s AS symbol, %s AS company_name, %s AS sector, %s AS market_cap) AS source
            ON target.SYMBOL = source.symbol
            WHEN MATCHED THEN
                UPDATE SET 
                    COMPANY_NAME = source.company_name,
                    SECTOR = source.sector,
                    MARKET_CAP = source.market_cap
            WHEN NOT MATCHED THEN
                INSERT (SYMBOL, COMPANY_NAME, SECTOR, MARKET_CAP)
                VALUES (source.symbol, source.company_name, source.sector, source.market_cap)
        """, (row['symbol'], row['company_name'], row.get('sector', 'Unknown'), row.get('market_cap', 0)))
    
    conn.commit()
    cursor.close()


def load_price_data(conn, df):
    """Load stock price data to TBL_STOCK_PRICE"""
    cursor = conn.cursor()
    
    # Expected columns: symbol, trade_date, open, high, low, close, volume
    required_cols = ['symbol', 'trade_date', 'close']
    if not all(col in df.columns for col in required_cols):
        print(f"  ⚠ Missing required columns. Found: {list(df.columns)}")
        return
    
    # Convert date format
    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
    
    # Get company IDs
    cursor.execute("SELECT SYMBOL, COMPANY_ID FROM TBL_COMPANY")
    symbol_to_id = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Insert price data
    insert_sql = """
        INSERT INTO TBL_STOCK_PRICE 
        (COMPANY_ID, TRADE_DATE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, CLOSE_PRICE, VOLUME, DATA_SOURCE, CREATED_AT)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    for _, row in df.iterrows():
        if row['symbol'] not in symbol_to_id:
            print(f"  ⚠ Symbol {row['symbol']} not in TBL_COMPANY, skipping")
            continue
        
        cursor.execute(insert_sql, (
            symbol_to_id[row['symbol']],
            row['trade_date'],
            row.get('open', row['close']),
            row.get('high', row['close']),
            row.get('low', row['close']),
            row['close'],
            row.get('volume', 0),
            'BATCH_S3',
            datetime.now()
        ))
    
    conn.commit()
    cursor.close()


def load_financial_data(conn, df):
    """Load financial data to TBL_FINANCIAL"""
    # Implementation similar to load_price_data
    print("  ℹ Financial data loading not yet implemented")
    pass


def main():
    parser = argparse.ArgumentParser(description='Process batch data from S3 to Snowflake')
    parser.add_argument('--bucket', default='egx-data-bucket', help='S3 bucket name')
    parser.add_argument('--prefix', default='batch/', help='S3 prefix/folder')
    parser.add_argument('--since', type=int, default=1, help='Process files modified in last N days')
    args = parser.parse_args()
    
    print("========================================")
    print("Batch Data Processor - Egyptian Exchange")
    print("========================================")
    print(f"Bucket: {args.bucket}")
    print(f"Prefix: {args.prefix}")
    print(f"Since: Last {args.since} days")
    print("")
    
    # Initialize clients
    s3_client = get_s3_client()
    conn = get_snowflake_connection()
    
    # List recent files
    files = list_recent_files(s3_client, args.bucket, args.prefix, args.since)
    
    if not files:
        print("No new files to process")
        return 0
    
    # Process each file
    success_count = 0
    fail_count = 0
    
    for file_info in files:
        if process_csv_file(s3_client, conn, args.bucket, file_info['key']):
            success_count += 1
        else:
            fail_count += 1
    
    conn.close()
    
    print("\n========================================")
    print("Processing Complete")
    print("========================================")
    print(f"✓ Success: {success_count} files")
    print(f"✗ Failed: {fail_count} files")
    print("")
    
    return 0 if fail_count == 0 else 1


if __name__ == '__main__':
    exit(main())
