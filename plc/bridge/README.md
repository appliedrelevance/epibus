# EpiBus Standalone PLC Bridge

## Overview

A standalone Python service that communicates with Frappe via REST API, designed to bridge Modbus devices with the EpiBus system.

## Architecture

- Completely standalone server
- No dependency on Frappe runtime
- Direct REST API communication
- Simple, focused design

## Prerequisites

- Python 3.8+
- `requests` library
- `pymodbus` library
- Frappe API access
- Modbus-enabled devices

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration and Startup

### Environment Configuration

1. Copy the template environment file:
   ```bash
   cp .env.template .env
   ```

2. Edit the `.env` file with your Frappe API credentials:
   ```
   FRAPPE_URL=https://your-frappe-site.com
   FRAPPE_API_KEY=your_api_key_here
   FRAPPE_API_SECRET=your_api_secret_here
   
   # Optional settings
   PLC_POLL_INTERVAL=1.0
   PLC_LOG_LEVEL=INFO
   ```

### Starting the PLC Bridge

Use the provided startup script:
```bash
./start_bridge.sh
```

This script will:
- Load configuration from the `.env` file
- Validate required environment variables
- Start the PLC Bridge with the appropriate parameters

### Manual Startup

Alternatively, run the bridge directly:
```bash
python bridge.py \
  --frappe-url https://your-frappe-site.com \
  --api-key YOUR_API_KEY \
  --api-secret YOUR_API_SECRET \
  [--poll-interval 1.0]
```

## Testing

The PLC Bridge includes a comprehensive test suite to verify its functionality.

### Running Tests

Use the provided test script:
```bash
./run_tests.sh
```

### Test Coverage

The test suite covers:
- Signal loading from Frappe
- Reading different types of Modbus signals
- Writing to Modbus signals
- Publishing signal updates to Frappe
- Signal polling and update detection

### Writing New Tests

To add new tests:
1. Add test methods to `test_bridge.py`
2. Follow the unittest framework conventions
3. Run the tests to verify your changes

## Signal Configuration

Signals are dynamically loaded from Frappe via the `get_all_signals` API endpoint:
- Configure Modbus Connections in Frappe
- Define Modbus Signals linked to those connections

## Logging

- Logs written to `plc_bridge.log`
- Console output for real-time monitoring

## Systemd Service (Optional)

Create a systemd service for automatic startup:

```ini
[Unit]
Description=EpiBus PLC Bridge
After=network.target

[Service]
WorkingDirectory=/path/to/plc/bridge
ExecStart=/path/to/plc/bridge/start_bridge.sh
Restart=always
User=your-user
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

- Verify Frappe URL and API credentials in `.env` file
- Check network connectivity
- Review `plc_bridge.log` for detailed errors
- Ensure Modbus devices are configured in Frappe

## Development Notes

- Modbus communication is implemented in the `_read_signal` and `_write_signal` methods
- Signal updates are published to Frappe via the `_publish_signal_update` method
- The bridge supports multiple Modbus connections simultaneously
- Each connection has its own Modbus client

## Key Characteristics

- Standalone service
- No Frappe runtime dependency
- Direct REST API communication
- Dynamically configured via Frappe documents