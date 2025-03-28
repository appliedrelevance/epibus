#!/bin/bash

# PLC Bridge Startup Script

# Change to script directory
cd "$(dirname "$0")"

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading configuration from .env file"
    export $(grep -v '^#' .env | xargs)
else
    echo "Warning: .env file not found. Using default or environment values."
    echo "Consider copying .env.template to .env and updating the values."
fi

# Check for required environment variables
if [ -z "$FRAPPE_URL" ] || [ -z "$FRAPPE_API_KEY" ] || [ -z "$FRAPPE_API_SECRET" ]; then
    echo "Error: Required environment variables not set."
    echo "Please ensure FRAPPE_URL, FRAPPE_API_KEY, and FRAPPE_API_SECRET are set in .env file or environment."
    exit 1
fi

# Start the PLC Bridge
echo "Starting PLC Bridge..."
echo "Frappe URL: $FRAPPE_URL"
echo "Poll Interval: ${PLC_POLL_INTERVAL:-1.0}"
echo "Log Level: ${PLC_LOG_LEVEL:-INFO}"

# Use the Python from the Frappe bench environment
BENCH_PYTHON="/home/intralogisticsuser/frappe-bench/env/bin/python"

if [ ! -f "$BENCH_PYTHON" ]; then
    echo "Error: Python executable not found at $BENCH_PYTHON"
    echo "Using system Python as fallback"
    BENCH_PYTHON="python3"
fi

echo "Using Python: $BENCH_PYTHON"

$BENCH_PYTHON bridge.py \
    --frappe-url "$FRAPPE_URL" \
    --api-key "$FRAPPE_API_KEY" \
    --api-secret "$FRAPPE_API_SECRET" \
    --poll-interval "${PLC_POLL_INTERVAL:-1.0}"

# Exit with the same code as the Python script
exit $?