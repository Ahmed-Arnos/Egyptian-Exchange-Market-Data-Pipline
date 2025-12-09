"""
Optimized batch loader - loads all S3 data using batch inserts for speed
"""

import boto3
import pandas as pd
import snowflake.connector
import io
from datetime import datetime
import re
import os

# AWS S3 Configuration
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
BUCKET_NAME = 'egx-data-bucket'

# Snowflake Configuration  
SNOWFLAKE_CONFIG = {
    'account': os.getenv('SNOWFLAKE_ACCOUNT', 'LPDTDON-IU51056'),
    'user': os.getenv('SNOWFLAKE_USER', 'AHMEDEHAB'),
    'password': os.getenv('SNOWFLAKE_PASSWORD'),
    'warehouse': 'COMPUTE_WH',
    'database': 'EGX_OPERATIONAL_DB'
}

def parse_volume(vol_str):
    """Parse volume strings like '4.39 M', '1.23 K' to integers"""
    if pd.isna(vol_str) or vol_str == '' or vol_str == '-':
        return None
    
    vol_str = str(vol_str).strip().replace(',', '')
    
    multiplier = 1
    if 'M' in vol_str.upper():
        multiplier = 1_000_000
        vol_str = vol_str.upper().replace('M', '').strip()
    elif 'K' in vol_str.upper():
        multiplier = 1_000
        vol_str = vol_str.upper().replace('K', '').strip()
    elif 'B' in vol_str.upper():
        multiplier = 1_000_000_000
        vol_str = vol_str.upper().replace('B', '').strip()
    
    try:
        return int(float(vol_str) * multiplier)
    except:
        return None

def parse_tvh_date(date_str):
    """Parse TVH date format: 'Mon 02 Dec '24' to datetime"""
    if pd.isna(date_str) or date_str == '':
        return None
    try:
        date_str = str(date_str).strip()
        date_obj = datetime.strptime(date_str, "%a %d %b '%y")
        return date_obj.strftime('%Y-%m-%d')
    except:
        return None

def clean_numeric(val):
    """Clean numeric values"""
    if pd.isna(val) or val == '' or val == '-':
        return None
    try:
        return float(str(val).replace(',', '').strip())
    except:
        return None

def load_companies(s3_client, conn):
    """Load company metadata"""
    print("\n📊 Loading companies...")
    cursor = conn.cursor()
    cursor.execute("USE SCHEMA OPERATIONAL")
    
    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key='batch/icons2.csv')
    df = pd.read_csv(io.BytesIO(obj['Body'].read()))
    
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO TBL_COMPANY (symbol, company_name, logo_url)
                VALUES (%s, %s, %s)
            """, (
                str(row['symbol']).strip(),
                str(row['name']).strip() if pd.notna(row['name']) else None,
                str(row['IconURL']).strip() if pd.notna(row['IconURL']) else None
            ))
        except:
            pass
    
    cursor.execute("SELECT COUNT(*) FROM TBL_COMPANY")
    count = cursor.fetchone()[0]
    print(f"✓ Loaded {count} companies")
    cursor.close()

def batch_load_prices(s3_client, conn):
    """Load all price data efficiently"""
    print("\n📈 Loading price data...")
    
    cursor = conn.cursor()
    cursor.execute("USE SCHEMA OPERATIONAL")
    
    # Get company mapping
    cursor.execute("SELECT symbol, company_id FROM TBL_COMPANY")
    symbol_to_id = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Prepare batch data
    all_prices = []
    
    # 1. Load TVH data
    print("  Processing TVH files...")
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix='batch/TVH/')
    tvh_files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.csv')]
    
    for i, key in enumerate(tvh_files, 1):
        try:
            symbol = key.split('/')[-1].replace('.csv', '').upper()
            if symbol not in symbol_to_id:
                continue
            
            company_id = symbol_to_id[symbol]
            obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
            df = pd.read_csv(io.BytesIO(obj['Body'].read()))
            
            for _, row in df.iterrows():
                trade_date = parse_tvh_date(row.get('Date'))
                if not trade_date:
                    continue
                
                all_prices.append((
                    company_id,
                    trade_date,
                    clean_numeric(row.get('Open')),
                    clean_numeric(row.get('High')),
                    clean_numeric(row.get('Low')),
                    clean_numeric(row.get('close')),
                    parse_volume(row.get('Volume')),
                    clean_numeric(row.get('Change')),
                    'TVH'
                ))
        except Exception as e:
            print(f"    Error on {key}: {e}")
        
        if i % 50 == 0:
            print(f"    Processed {i}/{len(tvh_files)} files, collected {len(all_prices):,} records")
    
    print(f"  Collected {len(all_prices):,} TVH price records")
    
    # Batch insert
    print("  Inserting into database...")
    for i in range(0, len(all_prices), 5000):
        batch = all_prices[i:i+5000]
        cursor.executemany("""
            INSERT INTO TBL_STOCK_PRICE 
            (company_id, trade_date, open_price, high_price, low_price, 
             close_price, volume, change_pct, data_source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, batch)
        print(f"    Inserted {i+len(batch):,}/{len(all_prices):,} records")
    
    cursor.execute("SELECT COUNT(*) FROM TBL_STOCK_PRICE")
    total = cursor.fetchone()[0]
    print(f"✓ Total price records in database: {total:,}")
    
    cursor.close()

def batch_load_financials(s3_client, conn):
    """Load financial data efficiently"""
    print("\n💰 Loading financial data...")
    
    cursor = conn.cursor()
    cursor.execute("USE SCHEMA OPERATIONAL")
    
    cursor.execute("SELECT symbol, company_id FROM TBL_COMPANY")
    symbol_to_id = {row[0]: row[1] for row in cursor.fetchall()}
    
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix='batch/finances/')
    finance_files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.csv')]
    
    all_financials = []
    
    for i, key in enumerate(finance_files, 1):
        try:
            # Extract symbol: batch/finances/AALR_finance.csv -> AALR
            symbol = key.split('/')[-1].replace('_finance.csv', '').upper()
            
            if symbol not in symbol_to_id:
                continue
            
            company_id = symbol_to_id[symbol]
            obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
            df = pd.read_csv(io.BytesIO(obj['Body'].read()))
            
            for _, row in df.iterrows():
                quarter = str(row.get('Quarter', '')).strip()
                if not quarter:
                    continue
                
                all_financials.append((
                    company_id,
                    quarter,
                    clean_numeric(row.get('total_revenue')),
                    clean_numeric(row.get('gross_profit')),
                    clean_numeric(row.get('net_income')),
                    clean_numeric(row.get('eps')),
                    clean_numeric(row.get('operating_expense')),
                    clean_numeric(row.get('total_assets')),
                    clean_numeric(row.get('total_liabilities')),
                    clean_numeric(row.get('free_cash_flow'))
                ))
        except Exception as e:
            print(f"  Error on {key}: {e}")
        
        if i % 50 == 0:
            print(f"  Processed {i}/{len(finance_files)} files, collected {len(all_financials):,} records")
    
    # Batch insert
    if all_financials:
        cursor.executemany("""
            INSERT INTO TBL_FINANCIAL 
            (company_id, quarter, total_revenue, gross_profit, net_income, 
             eps, operating_expense, total_assets, total_liabilities, free_cash_flow)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, all_financials)
    
    cursor.execute("SELECT COUNT(*) FROM TBL_FINANCIAL")
    total = cursor.fetchone()[0]
    print(f"✓ Loaded {total:,} financial records")
    
    cursor.close()

def batch_load_market_stats(s3_client, conn):
    """Load real-time market stats"""
    print("\n📊 Loading market statistics...")
    
    cursor = conn.cursor()
    cursor.execute("USE SCHEMA OPERATIONAL")
    
    cursor.execute("SELECT symbol, company_id FROM TBL_COMPANY")
    symbol_to_id = {row[0]: row[1] for row in cursor.fetchall()}
    
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix='batch/tradingview/')
    tv_files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.csv')]
    
    all_stats = []
    snapshot_dt = datetime.now()
    
    for i, key in enumerate(tv_files, 1):
        try:
            obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
            df = pd.read_csv(io.BytesIO(obj['Body'].read()))
            
            for _, row in df.iterrows():
                # Extract ticker symbol (first word from full company name)
                full_symbol = str(row.get('Symbol', '')).strip()
                if not full_symbol:
                    continue
                
                # Split and get first word (the ticker)
                symbol = full_symbol.split()[0].upper()
                
                if not symbol or symbol not in symbol_to_id:
                    continue
                
                company_id = symbol_to_id[symbol]
                
                all_stats.append((
                    company_id,
                    snapshot_dt,
                    clean_numeric(row.get('Price')),
                    clean_numeric(row.get('Change %')),
                    parse_volume(row.get('Volume')),
                    clean_numeric(row.get('Rel Volume')),
                    parse_volume(row.get('Market cap')),
                    clean_numeric(row.get('P/E')),
                    clean_numeric(row.get('EPS dil TTM')),
                    clean_numeric(row.get('EPS dil growth TTM YoY')),
                    clean_numeric(row.get('Div yield % TTM')),
                    str(row.get('Sector', '')).strip() if pd.notna(row.get('Sector')) else None,
                    str(row.get('Analyst Rating', '')).strip() if pd.notna(row.get('Analyst Rating')) else None
                ))
        except Exception as e:
            print(f"  Error on {key}: {e}")
        
        if i % 50 == 0:
            print(f"  Processed {i}/{len(tv_files)} files")
    
    # Batch insert  
    if all_stats:
        for i in range(0, len(all_stats), 5000):
            batch = all_stats[i:i+5000]
            cursor.executemany("""
                INSERT INTO TBL_MARKET_STAT 
                (company_id, snapshot_datetime, price, change_pct, volume, 
                 relative_volume, market_cap, pe_ratio, eps_ttm, eps_growth_yoy, 
                 div_yield_pct, sector, analyst_rating)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, batch)
    
    cursor.execute("SELECT COUNT(*) FROM TBL_MARKET_STAT")
    total = cursor.fetchone()[0]
    print(f"✓ Loaded {total:,} market stat records")
    
    # Update company sectors from market stats
    cursor.execute("""
        MERGE INTO TBL_COMPANY c
        USING (
            SELECT company_id, sector
            FROM TBL_MARKET_STAT 
            WHERE sector IS NOT NULL
            QUALIFY ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY snapshot_datetime DESC) = 1
        ) m
        ON c.company_id = m.company_id
        WHEN MATCHED THEN UPDATE SET c.sector = m.sector
    """)
    print("✓ Updated company sectors from market data")
    
    cursor.close()

def print_summary(conn):
    """Print final summary"""
    print("\n" + "="*80)
    print("📊 FINAL DATA SUMMARY")
    print("="*80 + "\n")
    
    cursor = conn.cursor()
    cursor.execute("USE SCHEMA OPERATIONAL")
    
    tables = [
        ('TBL_COMPANY', 'Companies with metadata'),
        ('TBL_INDEX', 'Market indices'),
        ('TBL_STOCK_PRICE', 'Historical price records'),
        ('TBL_FINANCIAL', 'Financial statement quarters'),
        ('TBL_MARKET_STAT', 'Real-time market snapshots')
    ]
    
    for table, desc in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{desc:.<45} {count:>10,} records")
    
    # Date range
    cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM TBL_STOCK_PRICE")
    result = cursor.fetchone()
    if result and result[0]:
        print(f"\nPrice data range: {result[0]} to {result[1]}")
    
    # Companies with complete data
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT CASE WHEN logo_url IS NOT NULL THEN company_id END) as with_logo,
            COUNT(DISTINCT CASE WHEN sector IS NOT NULL THEN company_id END) as with_sector
        FROM TBL_COMPANY
    """)
    result = cursor.fetchone()
    print(f"\nCompanies with logo: {result[0]}")
    print(f"Companies with sector: {result[1]}")
    
    cursor.close()

def main():
    """Main execution"""
    print("\n" + "="*80)
    print("🚀 BATCH LOADING ALL DATA FROM S3")
    print("="*80)
    
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    
    try:
        load_companies(s3_client, conn)
        batch_load_prices(s3_client, conn)
        batch_load_financials(s3_client, conn)
        batch_load_market_stats(s3_client, conn)
        print_summary(conn)
        
        print("\n" + "="*80)
        print("✅ ALL DATA LOADED SUCCESSFULLY!")
        print("="*80 + "\n")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
