"""
Load TradingView market statistics - fixes symbol extraction issue
"""

import boto3
import pandas as pd
import snowflake.connector
import io
from datetime import datetime
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
    if pd.isna(vol_str) or vol_str == '' or vol_str == '-' or vol_str == '—':
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

def clean_numeric(val):
    """Clean numeric values"""
    if pd.isna(val) or val == '' or val == '-' or val == '—':
        return None
    try:
        # Remove currency symbols and % signs
        val_str = str(val).replace('EGP', '').replace('%', '').replace(',', '').strip()
        # Remove + or - prefix
        if val_str.startswith('+') or val_str.startswith('−'):
            val_str = val_str[1:]
        return float(val_str)
    except:
        return None

def main():
    print("\n" + "="*80)
    print("📊 LOADING TRADINGVIEW MARKET STATISTICS")
    print("="*80 + "\n")
    
    # Connect to S3
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    
    # Connect to Snowflake
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    cursor = conn.cursor()
    cursor.execute("USE SCHEMA OPERATIONAL")
    
    # Get company mapping
    cursor.execute("SELECT symbol, company_id FROM TBL_COMPANY")
    symbol_to_id = {row[0]: row[1] for row in cursor.fetchall()}
    print(f"Loaded {len(symbol_to_id)} company symbols from database")
    
    # List tradingview files
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix='batch/tradingview/')
    tv_files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.csv')]
    print(f"Found {len(tv_files)} TradingView files")
    
    all_stats = []
    matched_symbols = set()
    unmatched_symbols = set()
    
    for i, key in enumerate(tv_files, 1):
        try:
            obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
            df = pd.read_csv(io.BytesIO(obj['Body'].read()))
            
            # Extract snapshot datetime from filename if possible
            snapshot_dt = datetime.now()
            
            for _, row in df.iterrows():
                # Extract ticker symbol (first word from full company name)
                full_symbol = str(row.get('Symbol', '')).strip()
                if not full_symbol:
                    continue
                
                # Split and get first word (the ticker)
                symbol = full_symbol.split()[0].upper()
                
                if not symbol:
                    continue
                
                if symbol not in symbol_to_id:
                    unmatched_symbols.add(symbol)
                    continue
                
                matched_symbols.add(symbol)
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
            print(f"  Processed {i}/{len(tv_files)} files, collected {len(all_stats):,} records")
    
    print(f"\n✓ Collected {len(all_stats):,} market stat records")
    print(f"✓ Matched {len(matched_symbols)} unique symbols")
    if unmatched_symbols:
        print(f"⚠ Unmatched symbols ({len(unmatched_symbols)}): {list(unmatched_symbols)[:10]}")
    
    # Batch insert  
    if all_stats:
        print(f"\nInserting {len(all_stats):,} records into TBL_MARKET_STAT...")
        for i in range(0, len(all_stats), 5000):
            batch = all_stats[i:i+5000]
            cursor.executemany("""
                INSERT INTO TBL_MARKET_STAT 
                (company_id, snapshot_datetime, price, change_pct, volume, 
                 relative_volume, market_cap, pe_ratio, eps_ttm, eps_growth_yoy, 
                 div_yield_pct, sector, analyst_rating)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, batch)
            print(f"  Inserted {min(i+5000, len(all_stats)):,}/{len(all_stats):,}")
    
    cursor.execute("SELECT COUNT(*) FROM TBL_MARKET_STAT")
    total = cursor.fetchone()[0]
    print(f"\n✓ Total market stat records in database: {total:,}")
    
    # Update company sectors from market stats
    print("\nUpdating company sectors from market data...")
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
    
    cursor.execute("SELECT COUNT(*) FROM TBL_COMPANY WHERE sector IS NOT NULL")
    companies_with_sector = cursor.fetchone()[0]
    print(f"✓ Updated {companies_with_sector} companies with sector information")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    print("✅ MARKET STATISTICS LOADED SUCCESSFULLY!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
