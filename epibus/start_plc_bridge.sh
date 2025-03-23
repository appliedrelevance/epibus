#!/bin/bash
# start_plc_bridge.sh - Manual startup script for PLC Bridge

# Set variables
BENCH_DIR="/workspace/development/frappe-bench"
APP_DIR="$BENCH_DIR/apps/epibus"
BRIDGE_SCRIPT="$APP_DIR/epibus/plc_bridge.py"
LOG_DIR="$BENCH_DIR/logs"
PID_FILE="$LOG_DIR/plc_bridge.pid"
LOG_FILE="$LOG_DIR/plc_bridge.log"

# Redis configuration - using Frappe's Docker network hostnames
REDIS_HOST="redis-queue"
REDIS_PORT="6379"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to check if Redis is accessible
check_redis() {
    echo "🔍 Checking Redis connection at $REDIS_HOST:$REDIS_PORT..."
    if redis-cli -h $REDIS_HOST -p $REDIS_PORT ping > /dev/null 2>&1; then
        echo "✅ Redis is accessible at $REDIS_HOST:$REDIS_PORT"
        return 0
    else
        echo "❌ Cannot connect to Redis at $REDIS_HOST:$REDIS_PORT"
        return 1
    fi
}

# Function to check if PLC bridge is running
is_plc_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null; then
            return 0  # Running
        else
            # PID file exists but process is not running
            rm "$PID_FILE"
        fi
    fi
    return 1  # Not running
}

# Function to start PLC bridge
start_bridge() {
    echo "🚀 Starting PLC Bridge..."
    
    # Check if already running
    if is_plc_running; then
        echo "⚠️ PLC Bridge is already running with PID $(cat "$PID_FILE")"
        return 1
    fi
    
    # Install required Python packages if not already installed
    echo "📦 Checking required packages..."
    $BENCH_DIR/env/bin/pip install redis pymodbus
    
    # Ensure Redis is accessible
    if ! check_redis; then
        echo "❌ Redis is not accessible, cannot continue"
        return 1
    fi
    
    # Start the bridge in background
    echo "🔄 Launching PLC Bridge process..."
    nohup $BENCH_DIR/env/bin/python "$BRIDGE_SCRIPT" --plc-host openplc --redis-host $REDIS_HOST --redis-port $REDIS_PORT > "$LOG_FILE" 2>&1 &
    
    # Save PID
    PID=$!
    echo $PID > "$PID_FILE"
    
    echo "✅ PLC Bridge started with PID $PID"
    echo "📝 Logs available at: $LOG_FILE"
    
    # Wait a moment and check if process is still running (to catch immediate failures)
    sleep 2
    if ! ps -p $PID > /dev/null; then
        echo "⚠️ PLC Bridge process exited immediately. Check logs for errors:"
        tail -n 10 "$LOG_FILE"
        rm "$PID_FILE"
        return 1
    fi
}

# Function to stop PLC bridge
stop_bridge() {
    echo "🛑 Stopping PLC Bridge..."
    
    # Check if running
    if ! is_plc_running; then
        echo "⚠️ PLC Bridge is not running"
        return 1
    fi
    
    # Get PID
    PID=$(cat "$PID_FILE")
    
    # Send SIGTERM to allow graceful shutdown
    kill -15 $PID
    
    # Wait for process to exit (max 5 seconds)
    for i in {1..5}; do
        if ! ps -p $PID > /dev/null; then
            break
        fi
        echo "⏳ Waiting for PLC Bridge to exit... ($i/5)"
        sleep 1
    done
    
    # If still running, force kill
    if ps -p $PID > /dev/null; then
        echo "⚠️ PLC Bridge did not exit gracefully, forcing termination..."
        kill -9 $PID
    fi
    
    # Remove PID file
    rm "$PID_FILE"
    
    echo "✅ PLC Bridge stopped"
}

# Function to check status
status_bridge() {
    # Check Redis status
    check_redis
    
    # Check PLC Bridge status
    if is_plc_running; then
        PID=$(cat "$PID_FILE")
        echo "✅ PLC Bridge is running with PID $PID"
        echo "📝 Logs available at: $LOG_FILE"
        echo "📊 Last 5 log entries:"
        tail -n 5 "$LOG_FILE"
    else
        echo "❌ PLC Bridge is not running"
    fi
}

# Function to restart bridge
restart_bridge() {
    echo "🔄 Restarting PLC Bridge..."
    stop_bridge
    sleep 2
    start_bridge
}

# Function to show help
show_help() {
    echo "PLC Bridge Manual Control Script"
    echo "--------------------------------"
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start    - Start the PLC Bridge"
    echo "  stop     - Stop the PLC Bridge"
    echo "  restart  - Restart the PLC Bridge"
    echo "  status   - Check the status of Redis and the PLC Bridge"
    echo "  logs     - Show the last 50 lines of logs"
    echo "  help     - Show this help message"
}

# Function to show logs
show_logs() {
    echo "📝 PLC Bridge Logs (last 50 lines):"
    tail -n 50 "$LOG_FILE"
    echo ""
    echo "To follow logs in real-time, use: tail -f $LOG_FILE"
}

# Main script logic
case "$1" in
    start)
        start_bridge
        ;;
    stop)
        stop_bridge
        ;;
    restart)
        restart_bridge
        ;;
    status)
        status_bridge
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "⚠️ Unknown command: $1"
        show_help
        exit 1
        ;;
esac

exit 0