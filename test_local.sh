#!/bin/bash

# Local test script for ExplainB Action
set -e

echo "🧪 Testing ExplainB Action locally..."

# Test DSNs - Use environment variables for security
# Set these environment variables before running:
# export TEST_DATABEND_DSN1='databend://user:pass@host1/tpcds_100'
# export TEST_DATABEND_DSN2='databend://user:pass@host2/tpcds_100'

if [ -z "$TEST_DATABEND_DSN1" ] || [ -z "$TEST_DATABEND_DSN2" ]; then
    echo "❌ Error: TEST_DATABEND_DSN1 and TEST_DATABEND_DSN2 environment variables must be set"
    echo "Example:"
    echo "  export TEST_DATABEND_DSN1='databend://user:pass@host1:port/tpcds_100'"
    echo "  export TEST_DATABEND_DSN2='databend://user:pass@host2:port/tpcds_100'"
    echo "  ./test_local.sh"
    exit 1
fi

export INPUT_BENDSQL_DSN1="$TEST_DATABEND_DSN1"
export INPUT_BENDSQL_DSN2="$TEST_DATABEND_DSN2"
export INPUT_OUTPUT_FILE='test-report.html'
export INPUT_RUNBEND='true'
export INPUT_VERBOSE='true'
export INPUT_QUERY_TIMEOUT='120'

echo "📊 DSN1: version-test-large"
echo "📊 DSN2: joincard-test-small"
echo "📄 Output: $INPUT_OUTPUT_FILE"

# Test connection first
echo ""
echo "🔍 Testing connections..."

echo "Testing DSN1..."
if bendsql --dsn="$INPUT_BENDSQL_DSN1" --query="SELECT 1;" > /dev/null 2>&1; then
    echo "✅ DSN1 connection successful"
else
    echo "❌ DSN1 connection failed"
    exit 1
fi

echo "Testing DSN2..."
if bendsql --dsn="$INPUT_BENDSQL_DSN2" --query="SELECT 1;" > /dev/null 2>&1; then
    echo "✅ DSN2 connection successful"
else
    echo "❌ DSN2 connection failed"
    exit 1
fi

# Run the analysis
echo ""
echo "🚀 Running ExplainB analysis..."

# Change to the action directory
cd "$(dirname "$0")"

# Set environment variables for explainb.py
export BENDSQL_DSN1="$INPUT_BENDSQL_DSN1"
export BENDSQL_DSN2="$INPUT_BENDSQL_DSN2"

# Run explainb.py with original wizard parameters
python3 src/explainb.py \
    --sql-file "sql/tpcds_100.sql" \
    --output "$INPUT_OUTPUT_FILE" \
    --timeout $INPUT_QUERY_TIMEOUT \
    --runbend \
    --verbose

# Check results
if [ -f "$INPUT_OUTPUT_FILE" ]; then
    REPORT_SIZE=$(wc -c < "$INPUT_OUTPUT_FILE")
    echo ""
    echo "✅ Test completed successfully!"
    echo "📊 Report generated: $INPUT_OUTPUT_FILE"
    echo "📏 Report size: $REPORT_SIZE bytes"
    echo ""
    echo "🌐 Open the report in your browser:"
    echo "   file://$(pwd)/$INPUT_OUTPUT_FILE"
else
    echo ""
    echo "❌ Test failed - no report generated"
    exit 1
fi