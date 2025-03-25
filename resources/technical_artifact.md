# Epibus Technical Artifact

## Overview

This document provides a technical overview of the Epibus system, focusing on the core modules and their interactions.

## Module Dependencies

*   **epibus.epibus.utils.signal\_handler.py:**
    *   Dependencies: `frappe`, `enum`, `epibus.epibus.utils.epinomy_logger`
    *   Description: Handles read/write operations for different Modbus signal types.
*   **epibus.epibus.utils.signal\_monitor.py:**
    *   Dependencies: `frappe`, `frappe.realtime`, `frappe.utils`, `epibus.epibus.doctype.modbus_connection.modbus_connection`, `epibus.epibus.doctype.modbus_action.modbus_action`, `epibus.epibus.doctype.modbus_event.modbus_event`, `epibus.epibus.utils.epinomy_logger`, `typing`, `collections`
    *   Description: Monitors Modbus signals and publishes changes via Frappe's realtime.
*   **epibus.epibus.utils.plc\_redis\_client.py:**
    *   Dependencies: `json`, `redis`, `frappe`, `typing`, `epibus.epibus.utils.epinomy_logger`
    *   Description: Redis client for communicating with the PLC bridge.
*   **epibus.epibus.utils.plc\_bridge\_adapter.py:**
    *   Dependencies: `frappe`, `epibus.utils.plc_redis_client`, `epibus.epibus.utils.epinomy_logger`
    *   Description: Provides functions for getting signals from and writing signals via the PLC bridge.

## Data Structures

*   **SignalType (Enum):** Defined in `signal_handler.py`. Represents the different Modbus signal types (e.g., DIGITAL\_OUTPUT, ANALOG\_INPUT).
*   **SignalHandler (Class):** Defined in `signal_handler.py`. Handles read/write operations for different Modbus signal types.
*   **SignalMonitor (Class):** Defined in `signal_monitor.py`. Monitors Modbus signals and publishes changes.
    *   `active_signals`: Dictionary storing the last known value of active signals.
    *   `device_signals`: Dictionary grouping signals by device for batch reading.
*   **PLCRedisClient (Class):** Defined in `plc_redis_client.py`. Redis client for communicating with the PLC bridge.

## API Specifications

*   **signal\_handler.py:**
    *   `SignalHandler.read(signal_type: str, address: int) -> Union[bool, float]`: Reads a value from a signal.
    *   `SignalHandler.write(signal_type: str, address: int, value: Union[bool, float]) -> None`: Writes a value to a signal.
*   **signal\_monitor.py:**
    *   `start_monitoring(**kwargs) -> Dict[str, Any]`: Starts monitoring a signal. This is the public API endpoint.
    *   `check_signals() -> None`: Polls active signals and publishes changes. Called by scheduler.
*   **plc\_redis\_client.py:**
    *   `PLCRedisClient.get_signals() -> List[Dict[str, Any]]`: Gets all Modbus signals and sends them to the PLC bridge.
    *   `PLCRedisClient.write_signal(signal_name: str, value: Union[bool, int, float]) -> bool`: Writes a signal value to the PLC.
*   **plc\_bridge\_adapter.py:**
    *   `get_signals_from_plc_bridge() -> list`: Retrieves signals from the PLC bridge.
    *   `write_signal_via_plc_bridge(signal_id, value) -> bool`: Writes a signal to the PLC bridge.

## Critical Algorithms

*   **Signal Monitoring (signal\_monitor.py):** The `SignalMonitor.check_signals()` method polls active signals, compares the current value to the last known value, and publishes updates to Frappe's realtime system when a change is detected.
*   **Signal Handling (plc\_redis\_client.py):** The `PLCRedisClient.handle_signal_update()` method processes signal updates received from the PLC bridge, logs the event, and publishes the update to Frappe's realtime system.
*   **Action Processing (plc\_redis\_client.py):** The `PLCRedisClient._process_signal_actions()` method finds and executes Modbus Actions triggered by a signal update, based on defined conditions.
*    **Signal Verification (plc_redis_client.py):** The `verify_signal_state` function verifies that a signal has been updated to the expected value in the PLC after a write operation.

## Data Flow

1.  **Signal Acquisition:** The `SignalMonitor` polls Modbus signals via the PLC bridge.
2.  **Data Processing:** The `SignalHandler` processes the raw signal data.
3.  **Realtime Updates:** The `SignalMonitor` publishes signal changes to Frappe's realtime system.
4.  **Frontend Display:** The frontend components subscribe to the realtime updates and display the signal values.
5.  **Action Execution:** When a signal change triggers a Modbus Action, the `PLCRedisClient` writes the new value to the PLC bridge.

## Frontend and Monitoring Applications

The frontend application, located in `apps/epibus/frontend/`, provides a user interface for monitoring and controlling Modbus signals. It subscribes to Frappe's realtime system to receive signal updates. The `ModbusDashboard.tsx` component is likely the main component for displaying the signals.

The `plc_monitor` directory contains various monitoring applications:

*   `plc_monitor/index.html` and `plc_monitor/app.js`: A basic monitoring application.
*   `redis_monitor.py`: Monitors Redis for signal updates.
*   `redis_to_socketio.py` and `redis_to_sse.py`: Scripts for streaming data to Socket.IO and SSE respectively.
*   `bridge_monitor.html`, `socketio_diagnostics.html`, `standalone_monitor.html`, `simple_monitor.html`, `direct_monitor.html`: Various HTML files for monitoring.

## API Documentation

### signal_handler.py
*   `SignalHandler.read(signal_type: str, address: int) -> Union[bool, float]`: Reads a value from a signal.
*   `SignalHandler.write(signal_type: str, address: int, value: Union[bool, float]) -> None`: Writes a value to a signal.

### signal_monitor.py
*   `start_monitoring(**kwargs) -> Dict[str, Any]`: Starts monitoring a signal. This is the public API endpoint.
*   `check_signals() -> None`: Polls active signals and publishes changes. Called by scheduler.

### plc_redis_client.py
*   `PLCRedisClient.get_signals() -> List[Dict[str, Any]]`: Gets all Modbus signals and sends them to the PLC bridge.
*   `PLCRedisClient.write_signal(signal_name: str, value: Union[bool, int, float]) -> bool`: Writes a signal value to the PLC.

### plc_bridge_adapter.py
*   `get_signals_from_plc_bridge() -> list`: Retrieves signals from the PLC bridge.
*   `write_signal_via_plc_bridge(signal_id, value) -> bool`: Writes a signal to the PLC bridge.

## Notes

*   The Epibus system uses Frappe's realtime system to publish signal updates to the frontend.
*   The system uses a PLC bridge to communicate with Modbus devices.
*   The `PLCRedisClient` uses Redis pubsub to listen for updates and send commands to the PLC bridge.