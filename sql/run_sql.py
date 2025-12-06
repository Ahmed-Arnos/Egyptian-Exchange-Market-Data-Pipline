#!/usr/bin/env python3
"""
Execute SQL scripts in Snowflake
Usage: python run_sql.py <sql_file_path>
"""

import os
import sys
import snowflake.connector
from pathlib import Path

def get_snowflake_connection():
    """Create Snowflake connection from environment variables"""
    return snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        role=os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'EGX_WH'),
    )

def execute_sql_file(sql_file_path):
    """Execute SQL file in Snowflake"""
    
    # Read SQL file
    sql_file = Path(sql_file_path)
    if not sql_file.exists():
        print(f"❌ Error: File not found: {sql_file_path}")
        sys.exit(1)
    
    print(f"\n📄 Reading SQL file: {sql_file.name}")
    sql_content = sql_file.read_text()
    
    # Split into statements (simple split by semicolon)
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
    
    print(f"📊 Found {len(statements)} SQL statements")
    print(f"🔌 Connecting to Snowflake...")
    
    try:
        # Connect to Snowflake
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        
        print(f"✅ Connected to {os.getenv('SNOWFLAKE_ACCOUNT')}")
        print(f"👤 User: {os.getenv('SNOWFLAKE_USER')}")
        print(f"🏭 Warehouse: {os.getenv('SNOWFLAKE_WAREHOUSE')}\n")
        
        # Execute each statement
        executed = 0
        failed = 0
        
        for i, statement in enumerate(statements, 1):
            # Skip comments and empty statements
            if not statement or statement.startswith('--'):
                continue
            
            # Show progress for long scripts
            if len(statements) > 10 and i % 10 == 0:
                print(f"⏳ Progress: {i}/{len(statements)} statements...")
            
            try:
                cursor.execute(statement)
                
                # Fetch results if available
                try:
                    results = cursor.fetchall()
                    if results:
                        for row in results:
                            # Print result rows (for validation queries)
                            print(f"   {' | '.join(str(val) for val in row)}")
                except:
                    pass  # No results to fetch
                
                executed += 1
                
            except snowflake.connector.errors.ProgrammingError as e:
                # Check if it's a harmless error (like IF EXISTS on non-existent object)
                error_msg = str(e).lower()
                if 'does not exist' in error_msg or 'already exists' in error_msg:
                    executed += 1
                else:
                    print(f"\n⚠️  Error in statement {i}:")
                    print(f"   {statement[:200]}...")
                    print(f"   Error: {e}\n")
                    failed += 1
        
        cursor.close()
        conn.close()
        
        # Summary
        print(f"\n{'='*60}")
        print(f"✅ Execution complete!")
        print(f"   Executed: {executed}/{len(statements)} statements")
        if failed > 0:
            print(f"   ⚠️  Failed: {failed} statements")
        print(f"{'='*60}\n")
        
        return failed == 0
        
    except snowflake.connector.errors.DatabaseError as e:
        print(f"\n❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python run_sql.py <sql_file_path>")
        sys.exit(1)
    
    # Check environment variables
    required_vars = ['SNOWFLAKE_ACCOUNT', 'SNOWFLAKE_USER', 'SNOWFLAKE_PASSWORD']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("\nRun: export $(cat egx_dw/.env | xargs)")
        sys.exit(1)
    
    sql_file = sys.argv[1]
    success = execute_sql_file(sql_file)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
