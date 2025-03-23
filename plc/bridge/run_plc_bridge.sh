#!/bin/bash
# run_plc_bridge.sh - Shell wrapper for manual_start_plc_bridge.py

# Set variables
BENCH_DIR="/workspace/development/frappe-bench"
APP_DIR="$BENCH_DIR/apps/epibus"
PYTHON_SCRIPT="$APP_DIR/epibus/manual_start_plc_bridge.py"

# Ensure the Python script is executable
chmod +x "$PYTHON_SCRIPT"

# Function to show help
show_help() {
    echo "PLC Bridge Control Script"
    echo "------------------------"
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start    - Start the PLC Bridge"
    echo "  stop     - Stop the PLC Bridge"
    echo "  restart  - Restart the PLC Bridge"
    echo "  status   - Check the status of the PLC Bridge"
    echo "  help     - Show this help message"
}

# Check if command is provided
if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

# Process command
case "$1" in
    start)
        echo "🚀 Starting PLC Bridge..."
        cd "$BENCH_DIR" && bench --site epinomy.localhost python "$PYTHON_SCRIPT" start
        ;;
    stop)
        echo "🛑 Stopping PLC Bridge..."
        cd "$BENCH_DIR" && bench --site epinomy.localhost python "$PYTHON_SCRIPT" stop
        ;;
    restart)
        echo "🔄 Restarting PLC Bridge..."
        cd "$BENCH_DIR" && bench --site epinomy.localhost python "$PYTHON_SCRIPT" restart
        ;;
    status)
        echo "📊 Checking PLC Bridge status..."
        cd "$BENCH_DIR" && bench --site epinomy.localhost python "$PYTHON_SCRIPT" status
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