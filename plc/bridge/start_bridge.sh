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

# Function to check if port 7654 is in use
check_port() {
    if netstat -tuln | grep -q ":7654 "; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to clean up any existing processes
cleanup_existing() {
    echo "Checking for existing bridge.py processes..."
    
    # Find any processes using port 7654
    if check_port; then
        echo "Port 7654 is in use. Attempting to identify and stop the process..."
        
        # Try to find PID using port 7654
        PORT_PID=$(lsof -t -i:7654 2>/dev/null)
        if [ -n "$PORT_PID" ]; then
            echo "Found process with PID $PORT_PID using port 7654"
            echo "Sending SIGTERM to allow graceful shutdown..."
            kill -15 $PORT_PID
            
            # Wait for up to 5 seconds for the port to be released
            for i in {1..5}; do
                if ! check_port; then
                    echo "Port 7654 has been released"
                    break
                fi
                echo "Waiting for port to be released... ($i/5)"
                sleep 1
            done
            
            # If port is still in use, force kill
            if check_port; then
                echo "Port still in use after timeout. Sending SIGKILL..."
                kill -9 $PORT_PID 2>/dev/null
                sleep 1
            fi
        else
            echo "Could not identify process using port 7654"
        fi
    fi
    
    # Also check for any lingering bridge.py processes
    BRIDGE_PIDS=$(pgrep -f "python.*bridge.py" 2>/dev/null)
    if [ -n "$BRIDGE_PIDS" ]; then
        echo "Found additional bridge.py processes. Stopping them..."
        echo $BRIDGE_PIDS | xargs kill -15
        sleep 2
        
        # Force kill any remaining processes
        REMAINING=$(pgrep -f "python.*bridge.py" 2>/dev/null)
        if [ -n "$REMAINING" ]; then
            echo "Some processes did not stop gracefully. Force killing..."
            echo $REMAINING | xargs kill -9
            sleep 1
        fi
    fi
    
    # Final check
    if check_port; then
        echo "WARNING: Port 7654 is still in use after cleanup attempts"
        echo "You may need to manually identify and stop the process"
        echo "Try: sudo lsof -i :7654"
        echo "Then: kill -9 <PID>"
        exit 1
    fi
}

# Clean up any existing processes
cleanup_existing

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

# Function to handle signals
handle_signal() {
    echo "Received signal, forwarding to PLC Bridge process..."
    if [ -n "$BRIDGE_PID" ]; then
        kill -15 $BRIDGE_PID
    fi
}

# Set up signal handlers
trap handle_signal SIGINT SIGTERM

# Start the Python process in the background and get its PID
$BENCH_PYTHON bridge.py \
    --frappe-url "$FRAPPE_URL" \
    --api-key "$FRAPPE_API_KEY" \
    --api-secret "$FRAPPE_API_SECRET" \
    --poll-interval "${PLC_POLL_INTERVAL:-1.0}" &

BRIDGE_PID=$!
echo "PLC Bridge started with PID: $BRIDGE_PID"

# Wait for the Python process to exit
wait "$BRIDGE_PID"
EXIT_CODE=$?

echo "PLC Bridge exited with code: $EXIT_CODE"
exit $EXIT_CODE