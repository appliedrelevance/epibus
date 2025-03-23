#!/bin/bash
# setup_plc_bridge.sh

# Set variables
BENCH_DIR="/home/frappe/frappe-bench"
APP_DIR="$BENCH_DIR/apps/epibus"
BRIDGE_SCRIPT="$APP_DIR/epibus/plc_bridge.py"
SUPERVISOR_CONF="/etc/supervisor/conf.d/plc_bridge.conf"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

# Install required Python packages
echo "Installing required packages..."
$BENCH_DIR/env/bin/pip install redis pymodbus

# Create supervisor configuration
echo "Creating supervisor configuration..."
cat > $SUPERVISOR_CONF << EOF
[program:plc_bridge]
command=$BENCH_DIR/env/bin/python $BRIDGE_SCRIPT --plc-host openplc --redis-host localhost
directory=$BENCH_DIR
user=frappe
autostart=true
autorestart=true
stdout_logfile=/var/log/supervisor/plc_bridge.log
stderr_logfile=/var/log/supervisor/plc_bridge_err.log
environment=PYTHONPATH="$BENCH_DIR/env/lib/python3.10/site-packages"
EOF

# Reload supervisor
echo "Reloading supervisor..."
supervisorctl reread
supervisorctl update

# Start the PLC bridge
echo "Starting PLC bridge..."
supervisorctl start plc_bridge

echo "Setup complete! PLC bridge is now running."
