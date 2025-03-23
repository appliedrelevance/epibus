# PLC Bridge Infrastructure

This directory contains the PLC bridge infrastructure for the Epibus application. The PLC bridge facilitates communication between the Frappe server and physical PLCs.

## Directory Structure

- **bridge/** - Core bridge functionality

  - `plc_bridge.py` - Main PLC bridge service
  - `init_redis_client.py` - Script to initialize the Redis client
  - `manual_start_plc_bridge.py` - Script to manually start/stop the PLC bridge
  - `run_plc_bridge.sh`, `setup_plc_bridge.sh`, `start_plc_bridge.sh` - Shell scripts for bridge operations

- **utils/** - Utility functions

  - `plc_bridge_adapter.py` - Adapter for the PLC bridge
  - `plc_redis_client.py` - Redis client for the PLC bridge

- **openplc/** - OpenPLC simulator and example files

  - `beachside_psm.py`, `intralogistics_psm.py` - Python SubModule files for OpenPLC
  - `modbus_client.py` - Diagnostic tool for Modbus communication
  - `test_modbus_tcp.py`, `test_beachside_psm.py` - Test files that serve as examples
  - `US15-B10-B1-PLC.json` - Configuration example

- **config/** - Configuration files

- **logs/** - Log files
  - `plc_bridge.log` - Log file for the PLC bridge

## Architecture

The PLC bridge infrastructure is part of a three-component architecture:

1. **Epibus Module** (apps/epibus/epibus) - Contains server-side Frappe functionality, including the plc.py API
2. **PLC Bridge Component** (apps/epibus/plc) - Dedicated solely to PLC communication functionality
3. **Frontend** (apps/epibus/frontend) - React-based user interface

This separation ensures clear boundaries between components, proper separation of concerns, and easier maintenance.
