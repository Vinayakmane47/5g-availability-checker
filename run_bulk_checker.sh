#!/bin/bash

# Bulk 5G Availability Checker Runner
# This script runs the bulk checker with optimal settings for expanding the database
# Enhanced with batch processing and retry mechanisms to handle loading errors

echo "Starting bulk 5G availability check for Melbourne CBD..."
echo "This will expand your database with new addresses and 5G availability data."
echo "Enhanced with retry mechanisms and batch processing to handle loading errors."
echo ""

# Check if we want to run a dry run first
if [ "$1" = "--dry-run" ]; then
    echo "Running dry run to see what addresses would be checked..."
    python bulk_checker.py --dry-run --limit 100 --batch-size 20
    echo ""
    echo "Dry run completed. Run without --dry-run to actually check addresses."
    exit 0
fi

# Check if we want to retry failed addresses
if [ "$1" = "--retry-failed" ]; then
    echo "RETRY MODE - Only retrying addresses that failed in previous runs..."
    python bulk_checker.py --retry-failed --workers 2 --batch-size 30
    echo ""
    echo "Retry completed!"
    exit 0
fi

# Default settings for optimal performance with error handling
WORKERS=2          # Reduced workers to avoid overwhelming Telstra servers
LIMIT=300          # Reduced limit for safer processing
BATCH_SIZE=30      # Smaller batches to avoid loading errors

echo "Settings (optimized for error handling):"
echo "  Workers: $WORKERS (reduced to avoid overwhelming servers)"
echo "  Address limit: $LIMIT (reduced for safer processing)"
echo "  Batch size: $BATCH_SIZE (smaller batches to avoid loading errors)"
echo ""

# Run the bulk checker
echo "Starting bulk check with enhanced error handling..."
python bulk_checker.py --workers $WORKERS --limit $LIMIT --batch-size $BATCH_SIZE

echo ""
echo "Bulk check completed!"
echo "Check bulk_checker.log for detailed logs."
echo "Results have been saved to results.csv"
echo ""

# Check if there are failed addresses to retry
if [ -f "failed_addresses.json" ]; then
    FAILED_COUNT=$(python -c "import json; print(len(json.load(open('failed_addresses.json'))))" 2>/dev/null || echo "0")
    if [ "$FAILED_COUNT" -gt 0 ]; then
        echo "WARNING: $FAILED_COUNT addresses failed and need retry."
        echo "Run './run_bulk_checker.sh --retry-failed' to retry them."
        echo ""
    fi
fi

echo "You can now use your web app to check 'Check from Database' to see the new results."
echo ""
echo "Additional options:"
echo "  ./run_bulk_checker.sh --dry-run     # See what would be checked"
echo "  ./run_bulk_checker.sh --retry-failed # Retry failed addresses" 