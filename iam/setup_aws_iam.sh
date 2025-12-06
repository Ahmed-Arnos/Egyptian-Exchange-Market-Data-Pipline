#!/usr/bin/env bash
# Setup AWS IAM role for Snowflake S3 access

set -e

ROLE_NAME="snowflake-s3-access-role"
POLICY_NAME="snowflake-s3-read-policy"
ACCOUNT_ID="622718430464"

echo "======================================================================="
echo "   AWS IAM Setup for Snowflake S3 Integration"
echo "======================================================================="
echo ""

# Step 1: Create IAM policy for S3 read access
echo "📝 Step 1: Creating IAM policy '${POLICY_NAME}'..."
echo ""

POLICY_ARN=$(aws iam create-policy \
    --policy-name ${POLICY_NAME} \
    --policy-document file://iam/snowflake-s3-read-policy.json \
    --description "Allows Snowflake to read from egx-data-bucket" \
    --query 'Policy.Arn' \
    --output text 2>&1) || {
    
    # If policy already exists, get its ARN
    echo "⚠️  Policy may already exist, retrieving ARN..."
    POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"
}

echo "✅ Policy ARN: ${POLICY_ARN}"
echo ""

# Step 2: Create IAM role with trust policy
echo "📝 Step 2: Creating IAM role '${ROLE_NAME}'..."
echo ""

aws iam create-role \
    --role-name ${ROLE_NAME} \
    --assume-role-policy-document file://iam/snowflake-trust-policy.json \
    --description "Allows Snowflake to access S3 bucket for data loading" || {
    
    echo "⚠️  Role may already exist, updating trust policy..."
    aws iam update-assume-role-policy \
        --role-name ${ROLE_NAME} \
        --policy-document file://iam/snowflake-trust-policy.json
}

echo "✅ Role created/updated"
echo ""

# Step 3: Attach policy to role
echo "📝 Step 3: Attaching policy to role..."
echo ""

aws iam attach-role-policy \
    --role-name ${ROLE_NAME} \
    --policy-arn ${POLICY_ARN}

echo "✅ Policy attached"
echo ""

# Step 4: Verify
echo "📝 Step 4: Verifying configuration..."
echo ""

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

echo "✅ Role ARN: ${ROLE_ARN}"
echo ""

# Display role details
aws iam get-role --role-name ${ROLE_NAME} --query 'Role.[RoleName,Arn,CreateDate]' --output table

echo ""
echo "======================================================================="
echo "   ✅ AWS IAM Configuration Complete!"
echo "======================================================================="
echo ""
echo "📋 Summary:"
echo "   - Role ARN: ${ROLE_ARN}"
echo "   - Policy: ${POLICY_NAME} (S3 read access to egx-data-bucket)"
echo "   - Trust Policy: Snowflake external user with External ID"
echo ""
echo "🎯 Next Steps:"
echo "   1. The Snowflake storage integration is already configured"
echo "   2. Run: ./setup_s3_pipeline.sh (it will continue from step 2)"
echo "   3. Or manually run: python sql/run_sql.py sql/05_load_s3_to_bronze.sql"
echo ""
echo "======================================================================="
