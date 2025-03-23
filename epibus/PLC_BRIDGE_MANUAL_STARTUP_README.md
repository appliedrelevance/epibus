# PLC Bridge Manual Startup Guide

This guide explains how to use the manual startup script for the PLC Bridge in development environments without supervisor.

## Overview

The PLC Bridge is a Python-based service that creates a high-performance communication channel between your PLC, Frappe/ERPNext server, and React dashboard. The original setup script (`setup_plc_bridge.sh`) depends on supervisorctl, which is not available in the Frappe development devcontainer.

This manual startup solution provides:

1. A fixed Redis client that properly handles communication between Frappe and the PLC Bridge
2. A Python script for managing the PLC Bridge process
3. A shell script wrapper for easy command-line usage

## Components

1. **Fixed Redis Client**

   - Located at `epibus/epibus/utils/plc_redis_client_fixed.py`
   - Properly subscribes to both signal updates and commands
   - Handles the "get_signals" command from the PLC Bridge

2. **Python Management Script**

   - Located at `epibus/epibus/manual_start_plc_bridge.py`
   - Initializes the fixed Redis client in Frappe
   - Manages the PLC Bridge process (start, stop, restart, status)

3. **Shell Script Wrapper**
   - Located at `epibus/epibus/run_plc_bridge.sh`
   - Provides a simple command-line interface
   - Runs the Python script in the Frappe environment

## Usage

### Starting the PLC Bridge

```bash
cd /workspace/development/frappe-bench
./apps/epibus/epibus/run_plc_bridge.sh start
```

### Checking Status

```bash
cd /workspace/development/frappe-bench
./apps/epibus/epibus/run_plc_bridge.sh status
```

### Stopping the PLC Bridge

```bash
cd /workspace/development/frappe-bench
./apps/epibus/epibus/run_plc_bridge.sh stop
```

### Restarting the PLC Bridge

```bash
cd /workspace/development/frappe-bench
./apps/epibus/epibus/run_plc_bridge.sh restart
```

## How It Works

1. The shell script wrapper (`run_plc_bridge.sh`) provides a simple command-line interface.
2. It runs the Python script (`manual_start_plc_bridge.py`) in the Frappe environment using the `bench` command.
3. The Python script initializes the fixed Redis client (`plc_redis_client_fixed.py`) in Frappe.
4. The fixed Redis client subscribes to both the "plc:signal_update" and "plc:command" channels in Redis.
5. When the PLC Bridge sends a "get_signals" command, the fixed Redis client responds by fetching the signals from the Frappe database and pushing them to the "plc:signals" list in Redis.
6. The PLC Bridge then receives the signals and starts monitoring them.

## Troubleshooting

### PLC Bridge Not Starting

Check the logs:

```bash
cat /workspace/development/frappe-bench/logs/plc_bridge.log
```

### Redis Connection Issues

Verify Redis is accessible:

```bash
redis-cli -h redis-queue ping
```

### Frappe Integration Issues

Check the Frappe logs:

```bash
cat /workspace/development/frappe-bench/logs/frappe.log
```

## Integration with Frappe

To ensure the PLC Bridge starts automatically with Frappe, you can add a line to your bench start script or create a custom command in the Procfile.

### Option 1: Add to Procfile

Add the following line to the Procfile:

```
plc_bridge: bash apps/epibus/epibus/run_plc_bridge.sh start
```

## Differences from Supervisor-based Setup

1. **Process Management**: Instead of supervisor, the process is managed by the Python script.
2. **Logging**: Logs are written to the Frappe logs directory instead of /var/log/supervisor.
3. **Startup**: The process is not automatically started on system boot, but can be integrated with Frappe's startup.
4. **Redis Client**: Uses a fixed version of the Redis client that properly handles commands from the PLC Bridge.

## Conclusion

This manual startup solution provides a robust alternative to the supervisor-based approach, allowing the PLC Bridge to run in development environments without supervisor. It includes comprehensive process management, logging, and user-friendly commands.
