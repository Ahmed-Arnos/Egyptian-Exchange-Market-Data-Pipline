"""
Load Index Membership (EGX30, EGX70) from S3 list files
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

def main():
    print("\n" + "="*80)
    print("📊 LOADING INDEX MEMBERSHIP")
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
    
    # Get mappings
    cursor.execute("SELECT symbol, company_id FROM TBL_COMPANY")
    symbol_to_id = {row[0]: row[1] for row in cursor.fetchall()}
    print(f"Loaded {len(symbol_to_id)} company symbols from database")
    
    cursor.execute("SELECT index_code, index_id FROM TBL_INDEX")
    index_to_id = {row[0]: row[1] for row in cursor.fetchall()}
    print(f"Loaded {len(index_to_id)} indices from database")
    print(f"Indices: {list(index_to_id.keys())}\n")
    
    # Index membership files
    index_files = [
        ('batch/EGX30_list - give the symbols_names_and_index.csv. file and an....csv', 'EGX30'),
        ('batch/EGX70_EWI - give the symbols_names_and_index.csv. file and an....csv', 'EGX70')
    ]
    
    all_memberships = []
    effective_date = datetime.now().date()
    
    for file_key, index_code in index_files:
        print(f"Processing {index_code}...")
        
        if index_code not in index_to_id:
            print(f"  ⚠ Index {index_code} not found in database, skipping")
            continue
        
        index_id = index_to_id[index_code]
        
        # Read CSV
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=file_key)
        df = pd.read_csv(io.BytesIO(obj['Body'].read()))
        
        matched = 0
        unmatched = []
        
        for _, row in df.iterrows():
            symbol = str(row['Symbol']).strip().upper()
            
            if symbol not in symbol_to_id:
                unmatched.append(symbol)
                continue
            
            company_id = symbol_to_id[symbol]
            
            # Equal weight for EGX70 EWI, will calculate proper weights later
            weight = 100.0 / len(df) if 'EWI' in index_code else None
            
            all_memberships.append((
                index_id,
                company_id,
                weight,
                effective_date,
                True  # is_current
            ))
            matched += 1
        
        print(f"  ✓ Matched {matched}/{len(df)} symbols")
        if unmatched:
            print(f"  ⚠ Unmatched symbols: {unmatched[:5]}")
    
    # Derive EGX100 from EGX30 + EGX70
    print(f"\nDeriving EGX100 membership (EGX30 + EGX70)...")
    egx100_companies = set()
    for membership in all_memberships:
        egx100_companies.add(membership[1])  # company_id
    
    if 'EGX100' in index_to_id:
        egx100_id = index_to_id['EGX100']
        for company_id in egx100_companies:
            all_memberships.append((
                egx100_id,
                company_id,
                None,  # weight
                effective_date,
                True  # is_current
            ))
        print(f"  ✓ Added {len(egx100_companies)} companies to EGX100")
    
    # Insert memberships
    print(f"\nInserting {len(all_memberships)} membership records...")
    cursor.executemany("""
        INSERT INTO TBL_INDEX_MEMBERSHIP 
        (index_id, company_id, weight, effective_date, is_current)
        VALUES (%s, %s, %s, %s, %s)
    """, all_memberships)
    
    cursor.execute("SELECT COUNT(*) FROM TBL_INDEX_MEMBERSHIP")
    total = cursor.fetchone()[0]
    print(f"✓ Total membership records in database: {total:,}")
    
    # Show summary
    print("\n" + "="*80)
    print("📊 INDEX MEMBERSHIP SUMMARY")
    print("="*80 + "\n")
    
    cursor.execute("""
        SELECT 
            i.index_code,
            i.index_name,
            COUNT(*) as members
        FROM TBL_INDEX_MEMBERSHIP m
        JOIN TBL_INDEX i ON m.index_id = i.index_id
        WHERE m.is_current = TRUE
        GROUP BY i.index_code, i.index_name
        ORDER BY members DESC
    """)
    
    for row in cursor.fetchall():
        print(f"  {row[0]:.<15} {row[1]:.<35} {row[2]:>3} companies")
    
    # Show sample members for each index
    print("\n📋 Sample Members:")
    for index_code in ['EGX30', 'EGX70', 'EGX100']:
        cursor.execute("""
            SELECT c.symbol, c.company_name
            FROM TBL_INDEX_MEMBERSHIP m
            JOIN TBL_INDEX i ON m.index_id = i.index_id
            JOIN TBL_COMPANY c ON m.company_id = c.company_id
            WHERE i.index_code = %s AND m.is_current = TRUE
            ORDER BY c.symbol
            LIMIT 10
        """, (index_code,))
        
        members = cursor.fetchall()
        if members:
            print(f"\n  {index_code} ({len(members)} shown):")
            for member in members:
                print(f"    • {member[0]}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    print("✅ INDEX MEMBERSHIP LOADED SUCCESSFULLY!")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
