#!/bin/bash

set -e

# Get input parameters
DSN1="${INPUT_BENDSQL_DSN1}"
DSN2="${INPUT_BENDSQL_DSN2}"
OUTPUT_FILE="${INPUT_OUTPUT_FILE:-report.html}"
RUNBEND="${INPUT_RUNBEND:-false}"
VERBOSE="${INPUT_VERBOSE:-false}"
QUERY_TIMEOUT="${INPUT_QUERY_TIMEOUT:-60}"

# Validate inputs
if [ -z "$DSN1" ]; then
    echo "Error: BENDSQL_DSN1 is required"
    exit 1
fi

if [ -z "$DSN2" ]; then
    echo "Error: BENDSQL_DSN2 is required"  
    exit 1
fi

echo "Starting ExplainB analysis..."
echo "DSN1: ${DSN1%:*}:***"  # Hide password in logs
echo "DSN2: ${DSN2%:*}:***"  # Hide password in logs
echo "Output file: $OUTPUT_FILE"
echo "Run Bend mode: $RUNBEND"

# Function to test database connection
test_connection() {
    local dsn=$1
    local name=$2
    
    echo "Testing connection to $name..."
    
    if timeout $QUERY_TIMEOUT bendsql --dsn="$dsn" --query="SELECT 1;" > /dev/null 2>&1; then
        echo "✓ Successfully connected to $name"
        return 0
    else
        echo "✗ Failed to connect to $name"
        return 1
    fi
}

# Test connections
if ! test_connection "$DSN1" "Database 1"; then
    echo "Failed to connect to first database"
    exit 1
fi

if ! test_connection "$DSN2" "Database 2"; then
    echo "Failed to connect to second database"
    exit 1
fi

# Always use the fixed TPC-DS SQL file
SQL_FILE="/app/sql/tpcds_100.sql"
echo "Using TPC-DS benchmark SQL file: $SQL_FILE"

# Set environment variables for explainb.py (wizard format)
export BENDSQL_DSN1="$DSN1"
export BENDSQL_DSN2="$DSN2"

# Run ExplainB analysis using explainb.py
echo "Running ExplainB analysis..."

# Build explainb.py command with original wizard parameters
CMD="python3 /app/src/explainb.py --sql-file '$SQL_FILE' --output '$OUTPUT_FILE' --timeout $QUERY_TIMEOUT"

if [ "$RUNBEND" = "true" ]; then
    CMD="$CMD --runbend"
fi

if [ "$VERBOSE" = "true" ]; then
    CMD="$CMD --verbose"
fi

# Execute the analysis
echo "Executing: explainb.py with specified parameters"
eval $CMD

# Check if report was generated successfully
if [ -f "$OUTPUT_FILE" ]; then
    echo "✓ Report generated successfully: $OUTPUT_FILE"
    
    # Set GitHub Action outputs
    echo "report-path=$OUTPUT_FILE" >> "$GITHUB_OUTPUT"
    echo "status=success" >> "$GITHUB_OUTPUT"
    
    # Show report size
    REPORT_SIZE=$(wc -c < "$OUTPUT_FILE")
    echo "Report size: $REPORT_SIZE bytes"
else
    echo "✗ Failed to generate report"
    echo "status=failure" >> "$GITHUB_OUTPUT"
    exit 1
fi

echo "ExplainB analysis completed successfully!"