# Archived PLC Bridge Components

This directory contains archived components from the original PLC Bridge implementation that have been replaced by the new PLC Worker implementation.

## Why These Files Were Archived

The original PLC Bridge architecture had several limitations:
- Multiple communication layers (Redis, standalone SocketIO, Frappe's realtime)
- Standalone process outside Frappe's worker system
- No built-in monitoring or automatic restart capabilities
- Redundant communication paths

The new PLC Worker implementation addresses these issues by:
- Integrating directly with Frappe's worker system
- Using Frappe's native realtime system for communication
- Providing automatic monitoring and restart through Supervisor
- Simplifying the architecture by eliminating redundant layers

## Directory Structure

- `plc_bridge/`: Original PLC Bridge scripts and configuration
- `redis_bridges/`: Redis to SocketIO and SSE bridge scripts
- `deprecated_utils/`: Deprecated utility modules like plc_bridge_adapter and plc_redis_client

## Migration Status

The migration from PLC Bridge to PLC Worker is complete. All functionality from the original implementation has been preserved in the new implementation.

For a detailed migration status report, see `apps/epibus/plc_worker_migration_status.md`.

## Reference

These files are kept for reference purposes only and should not be used in production. If you need to understand how the original implementation worked, these files provide that historical context.