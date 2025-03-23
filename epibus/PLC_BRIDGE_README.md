# PLC Bridge for EpiBus

## Overview

The PLC Bridge is a Python-based service that creates a high-performance communication channel between your PLC, Frappe/ERPNext server, and React dashboard. It addresses Frappe's threading limitations by running as a separate process and leveraging Redis for inter-process communication.

## Architecture

```
+-------------+                          +-------------+
|             |                          |             |
|    PLC      |<----- ModbusTCP -------->|  PLC Bridge |
|  (OpenPLC)  |                          |  (Python)   |
|             |                          |             |
+-------------+                          +-------------+
      |                                        |
      |                                        |
      v                                        v
+-------------+      +-------------+    +-------------+
|             |      |             |    |             |
|   Frappe    |<---->|    Redis    |<-->|   React     |
|   Server    |      |  Pub/Sub    |    | Dashboard   |
|             |      |             |    |             |
+-------------+      +-------------+    +-------------+
```

## Key Features

- **<200ms Latency**: Polls the PLC at 50ms intervals for real-time updates
- **Frappe-Independent**: Runs outside Frappe's process space to avoid threading issues
- **Pymodbus Integration**: Leverages your existing pymodbus investment
- **Redis Pub/Sub**: Fast, efficient communication between components
- **Supervisor Managed**: Automatically restarts if it crashes
- **Comprehensive Logging**: Detailed logs with emoji indicators for quick visual scanning

## Components

1. **Python PLC Bridge**

   - Located at `epibus/epibus/plc_bridge.py`
   - Handles direct Modbus communication and Redis messaging

2. **Redis Client**

   - Located at `epibus/epibus/utils/plc_redis_client.py`
   - Provides Frappe-side Redis communication

3. **API Endpoints**

   - Located at `epibus/epibus/api/plc.py`
   - Exposes HTTP endpoints for React

4. **React Components**
   - Located in `epibus/frontend/` directory
   - Provides UI components for monitoring and control

## Installation

### Prerequisites

- Frappe/ERPNext server
- Redis server
- Python 3.8+
- Supervisor
- Network access to the PLC

### Installation Steps

1. The code has been written to your EpiBus directory. You'll need to:

   ```bash
   # Make the setup script executable
   chmod +x ~/frappe-bench/apps/epibus/epibus/setup_plc_bridge.sh

   # Run the setup script as root
   sudo ~/frappe-bench/apps/epibus/epibus/setup_plc_bridge.sh
   ```

2. Add the whitelist entries to your hooks.py:

   ```python
   # Add this to hooks.py
   whitelisted_methods = {
       "epibus.epibus.api.plc.get_signals": ["System Manager", "Modbus Administrator", "Modbus User"],
       "epibus.epibus.api.plc.update_signal": ["System Manager", "Modbus Administrator", "Modbus User"],
       "epibus.epibus.api.plc.get_plc_status": ["System Manager", "Modbus Administrator", "Modbus User"],
       "epibus.epibus.api.plc.reload_signals": ["System Manager", "Modbus Administrator", "Modbus User"]
   }
   ```

3. Install the required Python packages:

   ```bash
   ~/frappe-bench/env/bin/pip install redis pymodbus
   ```

4. Restart the Frappe web server:

   ```bash
   bench restart web
   ```

5. Ensure the React components are properly integrated into your frontend build process.

## React Components

The following React components are available in the `epibus/frontend/src/` directory:

### 1. useSignalMonitor Hook

Located at `epibus/frontend/src/hooks/useSignalMonitor.ts`, this hook provides:

- Real-time signal updates via socket.io
- Signal write functionality
- Connection status monitoring

```typescript
import { useSignalMonitor } from "../hooks/useSignalMonitor";

// Inside your component
const { signals, writeSignal, connected } = useSignalMonitor();
```

### 2. PLCStatus Component

Located at `epibus/frontend/src/components/PLCStatus.tsx`, this component provides:

- Connection status indicator
- PLC cycle status indicator
- Error state monitoring

```typescript
import { PLCStatus } from "../components/PLCStatus";

// Inside your component
<PLCStatus className="mb-4" />;
```

### 3. SignalControl Component

Located at `epibus/frontend/src/components/SignalControl.tsx`, this component provides:

- Digital output controls (toggles)
- Analog output controls (sliders)
- Loading state indicators

```typescript
import { SignalControl } from "../components/SignalControl";

// Inside your component
<SignalControl signalName="SIGNAL_NAME" label="User Friendly Label" />;
```

## Usage

### Monitoring the PLC Bridge

You can check the status of the PLC Bridge with:

```bash
sudo supervisorctl status plc_bridge
```

View the logs with:

```bash
sudo tail -f /var/log/supervisor/plc_bridge.log
```

### Redis Channels

The PLC Bridge uses the following Redis channels:

- `plc:command` - Commands to the PLC bridge
- `plc:signal_update` - Signal updates from the PLC
- `plc:status` - Status updates from the PLC bridge

### Available Commands

You can send commands to the PLC Bridge via Redis:

```python
import redis
import json

r = redis.Redis()
r.publish("plc:command", json.dumps({
    "command": "write_signal",
    "signal": "SIGNAL_NAME",
    "value": True  # or False, or a number
}))
```

Available commands:

- `write_signal` - Write a value to a signal
- `get_signals` - Request a list of signals
- `reload_signals` - Reload signals from the database
- `status` - Request current status

### API Endpoints

The following API endpoints are available:

- `epibus.epibus.api.plc.get_signals` - Get all Modbus signals
- `epibus.epibus.api.plc.update_signal` - Update a signal value
- `epibus.epibus.api.plc.get_plc_status` - Get current PLC status
- `epibus.epibus.api.plc.reload_signals` - Reload signals in the PLC bridge

### Dashboard Integration Example

Here's an example of integrating the components into a dashboard:

```tsx
import React from "react";
import { PLCStatus } from "../components/PLCStatus";
import { SignalControl } from "../components/SignalControl";

export function PLCDashboard() {
  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">PLC Dashboard</h1>

      <PLCStatus className="mb-4" />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <SignalControl
          signalName="WAREHOUSE-ROBOT-1-CYCLE_RUNNING"
          label="PLC Cycle"
        />
        <SignalControl signalName="-PICK BIN 01" label="Pick Bin 1" />
        <SignalControl signalName="-TO RECEIVING STA 1" label="To Receiving" />
        {/* Add more controls as needed */}
      </div>
    </div>
  );
}
```

## Redis Communication Protocol

### Signal Updates (plc:signal_update)

```json
{
  "name": "signal_name",
  "value": true|false|123,
  "timestamp": 1234567890.123
}
```

### Status Updates (plc:status)

```json
{
  "connected": true|false,
  "running": true|false,
  "signal_count": 123,
  "timestamp": 1234567890.123
}
```

### Command Format (plc:command)

```json
{
  "command": "write_signal",
  "signal": "signal_name",
  "value": true|false|123
}
```

## Troubleshooting

### Common Issues

1. **PLC Bridge not starting**

   - Check the logs: `sudo tail -f /var/log/supervisor/plc_bridge.log`
   - Check if supervisor is running: `sudo systemctl status supervisor`

2. **PLC Bridge not connecting to PLC**

   - Check network connectivity: `ping openplc`
   - Verify PLC is accepting Modbus TCP connections

3. **Redis connection errors**

   - Check if Redis is running: `redis-cli ping`
   - Verify Redis configuration in site_config.json

4. **React dashboard not updating**
   - Check browser console for socket.io errors
   - Verify real-time updates are enabled in Frappe

### Logs

- PLC Bridge logs: `/var/log/supervisor/plc_bridge.log`
- Frappe logs: `~/frappe-bench/logs/frappe.log`

## Building and Deploying React Components

To integrate the React components with your frontend:

1. Ensure the component files are correctly placed in the `epibus/frontend/src/` directory
2. Install required dependencies:

   ```bash
   cd ~/frappe-bench/apps/epibus/frontend
   yarn add socket.io-client
   ```

3. Import the components in your application
4. Build the frontend:

   ```bash
   cd ~/frappe-bench/apps/epibus/frontend
   yarn build
   ```

5. The built files will be automatically available to your Frappe application

## Best Practices

1. **Signal Grouping**

   - Group related signals in the React UI
   - Use consistent naming conventions

2. **Error Handling**

   - Always check for error states
   - Implement proper fallbacks

3. **Performance Optimization**
   - Only update the UI when signals change
   - Use batch reads for related signals

## Conclusion

The PLC Bridge provides a robust, high-performance solution for integrating your PLC with Frappe/ERPNext while addressing the threading limitations of the Frappe framework. By running as a separate process and using Redis for communication, it ensures reliable operation and sub-200ms latency for real-time monitoring and control.
