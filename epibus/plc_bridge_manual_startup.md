# PLC Bridge Manual Startup Plan

## Overview

This document outlines a plan for creating a manual startup script for the PLC Bridge that doesn't depend on supervisorctl, which is not available in the Frappe development devcontainer.

## Current Setup Analysis

The current setup script (`setup_plc_bridge.sh`) depends on supervisorctl and does the following:

1. Installs required Python packages (redis, pymodbus)
2. Creates a supervisor configuration file
3. Reloads supervisor
4. Starts the PLC bridge using supervisor

## Manual Startup Script Plan

The new manual startup script will:

1. Install required Python packages
2. Start the PLC bridge directly as a background process
3. Provide a way to stop the PLC bridge
4. Provide clear console output about the startup process

## Implementation Details

### Script Structure

The script will be named `start_plc_bridge.sh` and will have the following structure:

```bash
#!/bin/bash
# start_plc_bridge.sh - Manual startup script for PLC Bridge

# Set variables
BENCH_DIR="/workspace/development/frappe-bench"
APP_DIR="$BENCH_DIR/apps/epibus"
BRIDGE_SCRIPT="$APP_DIR/epibus/plc_bridge.py"
LOG_DIR="$BENCH_DIR/logs"
PID_FILE="$LOG_DIR/plc_bridge.pid"
LOG_FILE="$LOG_DIR/plc_bridge.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to check if PLC bridge is running
is_running() {
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
    if is_running; then
        echo "⚠️ PLC Bridge is already running with PID $(cat "$PID_FILE")"
        return 1
    fi

    # Install required Python packages if not already installed
    echo "📦 Checking required packages..."
    $BENCH_DIR/env/bin/pip install redis pymodbus

    # Start the bridge in background
    echo "🔄 Launching PLC Bridge process..."
    nohup $BENCH_DIR/env/bin/python "$BRIDGE_SCRIPT" --plc-host openplc --redis-host localhost > "$LOG_FILE" 2>&1 &

    # Save PID
    PID=$!
    echo $PID > "$PID_FILE"

    echo "✅ PLC Bridge started with PID $PID"
    echo "📝 Logs available at: $LOG_FILE"
}

# Function to stop PLC bridge
stop_bridge() {
    echo "🛑 Stopping PLC Bridge..."

    # Check if running
    if ! is_running; then
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
    if is_running; then
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
    echo "  status   - Check the status of the PLC Bridge"
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
```

### Usage Instructions

1. Make the script executable:

   ```bash
   chmod +x ~/frappe-bench/apps/epibus/epibus/start_plc_bridge.sh
   ```

2. Start the PLC Bridge:

   ```bash
   ~/frappe-bench/apps/epibus/epibus/start_plc_bridge.sh start
   ```

3. Check status:

   ```bash
   ~/frappe-bench/apps/epibus/epibus/start_plc_bridge.sh status
   ```

4. View logs:

   ```bash
   ~/frappe-bench/apps/epibus/epibus/start_plc_bridge.sh logs
   ```

5. Stop the PLC Bridge:
   ```bash
   ~/frappe-bench/apps/epibus/epibus/start_plc_bridge.sh stop
   ```

## Integration with Frappe

To ensure the PLC Bridge starts automatically with Frappe, you can add a line to your bench start script or create a custom command in the Procfile.

### Option 1: Add to bench start script

Create a custom bench command that starts both Frappe and the PLC Bridge.

### Option 2: Add to Procfile

Add the following line to the Procfile:

```
plc_bridge: bash apps/epibus/epibus/start_plc_bridge.sh start
```

## Conclusion

This manual startup script provides a robust alternative to the supervisor-based approach, allowing the PLC Bridge to run in development environments without supervisor. It includes comprehensive process management, logging, and user-friendly commands.
