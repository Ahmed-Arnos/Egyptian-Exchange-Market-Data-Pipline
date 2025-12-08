#!/usr/bin/env python3
"""
Check AWS S3 Bucket Contents

Lists all objects in the EGX data bucket and analyzes the structure.
"""

import os
import sys
from datetime import datetime

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("ERROR: boto3 not installed. Run: pip install boto3")
    sys.exit(1)


def check_s3_bucket(bucket_name='egx-data-bucket'):
    """Check S3 bucket contents and structure"""
    
    print("=" * 80)
    print("AWS S3 BUCKET ANALYSIS")
    print("=" * 80)
    print(f"Bucket: {bucket_name}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Check if bucket exists and is accessible
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✓ Bucket '{bucket_name}' is accessible")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"✗ Bucket '{bucket_name}' does not exist")
                return
            elif error_code == '403':
                print(f"✗ Access denied to bucket '{bucket_name}'")
                return
            else:
                print(f"✗ Error accessing bucket: {e}")
                return
        
        print("\n" + "-" * 80)
        print("BUCKET CONTENTS:")
        print("-" * 80)
        
        # List all objects
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        
        objects_by_prefix = {}
        total_objects = 0
        total_size = 0
        
        for page in pages:
            if 'Contents' not in page:
                print("Bucket is empty")
                return
            
            for obj in page['Contents']:
                key = obj['Key']
                size = obj['Size']
                last_modified = obj['LastModified']
                
                # Extract prefix (directory structure)
                prefix = '/'.join(key.split('/')[:-1]) if '/' in key else 'root'
                
                if prefix not in objects_by_prefix:
                    objects_by_prefix[prefix] = {
                        'count': 0,
                        'total_size': 0,
                        'files': [],
                        'extensions': set()
                    }
                
                objects_by_prefix[prefix]['count'] += 1
                objects_by_prefix[prefix]['total_size'] += size
                objects_by_prefix[prefix]['files'].append({
                    'name': key,
                    'size': size,
                    'last_modified': last_modified
                })
                
                # Track file extensions
                if '.' in key:
                    ext = key.split('.')[-1].lower()
                    objects_by_prefix[prefix]['extensions'].add(ext)
                
                total_objects += 1
                total_size += size
        
        # Print summary by prefix
        print("\nDIRECTORY STRUCTURE:\n")
        
        for prefix in sorted(objects_by_prefix.keys()):
            data = objects_by_prefix[prefix]
            size_mb = data['total_size'] / (1024 * 1024)
            
            print(f"📁 {prefix}/")
            print(f"   Files: {data['count']}")
            print(f"   Total Size: {size_mb:.2f} MB")
            print(f"   File Types: {', '.join(sorted(data['extensions']))}")
            
            # Show first 5 files as examples
            print(f"   Sample Files:")
            for file_info in data['files'][:5]:
                file_size_kb = file_info['size'] / 1024
                print(f"      - {file_info['name'].split('/')[-1]} ({file_size_kb:.2f} KB) - {file_info['last_modified'].strftime('%Y-%m-%d')}")
            
            if data['count'] > 5:
                print(f"      ... and {data['count'] - 5} more files")
            print()
        
        # Overall summary
        print("-" * 80)
        print("OVERALL SUMMARY:")
        print("-" * 80)
        print(f"Total Directories: {len(objects_by_prefix)}")
        print(f"Total Files: {total_objects}")
        print(f"Total Size: {total_size / (1024 * 1024):.2f} MB ({total_size / (1024 * 1024 * 1024):.3f} GB)")
        
        # Data type analysis
        print("\n" + "-" * 80)
        print("DATA TYPE ANALYSIS:")
        print("-" * 80)
        
        all_extensions = {}
        for prefix_data in objects_by_prefix.values():
            for ext in prefix_data['extensions']:
                all_extensions[ext] = all_extensions.get(ext, 0) + 1
        
        for ext, count in sorted(all_extensions.items(), key=lambda x: x[1], reverse=True):
            print(f"  .{ext}: {count} directories")
        
        # Expected structure check
        print("\n" + "-" * 80)
        print("EXPECTED DATA SOURCES CHECK:")
        print("-" * 80)
        
        expected_paths = {
            'historical/stock_prices/': 'Historical stock price CSVs',
            'historical/': 'General historical data',
            'data/historical/': 'Alternative historical path',
            'streaming/': 'Real-time streaming data',
            'metadata/companies/': 'Company metadata (logos, info)',
            'metadata/logos/': 'Company logos',
            'logos/': 'Alternative logos path',
            'kaggle/raw/': 'Kaggle datasets',
            'indices/': 'Index composition files (EGX30/70/100)',
        }
        
        for path, description in expected_paths.items():
            found = any(prefix.startswith(path.rstrip('/')) for prefix in objects_by_prefix.keys())
            status = "✓ FOUND" if found else "✗ MISSING"
            print(f"{status}: {path} - {description}")
        
        print("\n" + "=" * 80)
        
        # Recommendations
        print("\nRECOMMENDATIONS:")
        print("-" * 80)
        
        if total_objects == 0:
            print("⚠ Bucket is empty. Upload historical data to begin.")
        elif total_objects < 50:
            print("⚠ Limited data available. Consider uploading more historical data.")
        else:
            print("✓ Sufficient data available for processing.")
        
        missing_paths = [path for path, _ in expected_paths.items() 
                        if not any(prefix.startswith(path.rstrip('/')) for prefix in objects_by_prefix.keys())]
        
        if missing_paths:
            print(f"\n⚠ Missing expected directories: {', '.join(missing_paths)}")
            print("  Consider organizing data according to the expected structure.")
        
    except NoCredentialsError:
        print("\n✗ AWS credentials not found!")
        print("\nPlease configure AWS credentials using one of these methods:")
        print("  1. Environment variables:")
        print("     export AWS_ACCESS_KEY_ID='your_key'")
        print("     export AWS_SECRET_ACCESS_KEY='your_secret'")
        print("  2. AWS CLI configuration:")
        print("     aws configure")
        print("  3. Create ~/.aws/credentials file")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Check AWS S3 bucket contents')
    parser.add_argument('--bucket', default='egx-data-bucket', help='S3 bucket name')
    
    args = parser.parse_args()
    
    check_s3_bucket(args.bucket)
