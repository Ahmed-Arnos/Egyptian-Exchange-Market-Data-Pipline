#!/usr/bin/env bash
# Quick setup script for S3 to Snowflake pipeline

set -e

echo "======================================================================="
echo "   EGX Data Pipeline: S3 → Snowflake → Grafana Setup"
echo "======================================================================="
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."

if [ ! -f "egx_dw/.env" ]; then
    echo "❌ Missing egx_dw/.env file"
    echo "   Please create it with Snowflake credentials"
    exit 1
fi

if [ ! -d "egx_dw/venv" ]; then
    echo "❌ Virtual environment not found"
    echo "   Run: python -m venv egx_dw/venv && source egx_dw/venv/bin/activate && pip install snowflake-connector-python python-dotenv"
    exit 1
fi

echo "✅ Prerequisites OK"
echo ""

# Activate venv
source egx_dw/venv/bin/activate

# Step 1: S3 Integration
echo "======================================================================="
echo "Step 1: Setting up S3 integration..."
echo "======================================================================="
echo ""
python sql/run_sql.py sql/04_setup_s3_integration.sql

echo ""
echo "⚠️  IMPORTANT: AWS IAM Configuration Required"
echo ""
echo "1. Run in Snowflake: DESC STORAGE INTEGRATION s3_egx_integration;"
echo "2. Note the STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID"
echo "3. Create AWS IAM role 'snowflake-s3-access-role' with trust policy:"
echo "   {\"Effect\": \"Allow\", \"Principal\": {\"AWS\": \"<ARN>\"}, \"Action\": \"sts:AssumeRole\", \"Condition\": {\"StringEquals\": {\"sts:ExternalId\": \"<ID>\"}}}"
echo "4. Attach S3 read policy to the role"
echo ""
read -p "Press Enter after completing AWS IAM setup..."

# Step 2: Load Bronze
echo ""
echo "======================================================================="
echo "Step 2: Loading data from S3 to Bronze layer..."
echo "======================================================================="
echo ""
python sql/run_sql.py sql/05_load_s3_to_bronze.sql

# Step 3: Create Silver
echo ""
echo "======================================================================="
echo "Step 3: Creating Silver layer (cleaned & unified)..."
echo "======================================================================="
echo ""
python sql/run_sql.py sql/06_create_silver_layer.sql

# Step 4: Create Gold
echo ""
echo "======================================================================="
echo "Step 4: Creating Gold layer (analytics-ready)..."
echo "======================================================================="
echo ""
python sql/run_sql.py sql/07_create_gold_layer.sql

# Summary
echo ""
echo "======================================================================="
echo "   ✅ Pipeline Setup Complete!"
echo "======================================================================="
echo ""
echo "📊 Data Layers Created:"
echo "   - BRONZE: Raw data from S3 (historical CSV + streaming JSON)"
echo "   - SILVER: Cleaned & unified OHLCV data"
echo "   - GOLD: Analytics-ready fact/dimension tables"
echo ""
echo "🎯 Next Steps:"
echo "   1. Configure Grafana:"
echo "      - Install: grafana-cli plugins install michelin-snowflake-datasource"
echo "      - Add Snowflake datasource (see docs/S3_SNOWFLAKE_PIPELINE_GUIDE.md)"
echo ""
echo "   2. Create Grafana dashboard using Gold views:"
echo "      - vw_gold_market_snapshot (latest prices)"
echo "      - vw_gold_price_history (time series)"
echo "      - vw_gold_top_movers (gainers/losers)"
echo "      - vw_gold_volume_leaders (volume analysis)"
echo ""
echo "   3. Set up incremental updates:"
echo "      - Option A: Snowpipe (automated, continuous)"
echo "      - Option B: Scheduled tasks (hourly/daily)"
echo "      - Option C: Manual refresh (this script)"
echo ""
echo "📖 Full documentation: docs/S3_SNOWFLAKE_PIPELINE_GUIDE.md"
echo ""
echo "======================================================================="
