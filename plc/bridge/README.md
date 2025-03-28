# EpiBus PLC Bridge

## Overview

A Python service that communicates with Frappe via REST API, designed to bridge Modbus devices with the EpiBus system. The PLC Bridge can run either as a standalone service or integrated with the Frappe bench.

## Architecture

- Runs as a supervisor-managed service in production
- Can also run as a standalone server for development
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

### As Part of Frappe Bench (Recommended for Production)

When the EpiBus app is installed in a Frappe bench, the PLC Bridge is automatically configured to run as a supervisor-managed service. This happens through the `after_install` hook which:

1. Creates a supervisor configuration file (`config/supervisor/plc_bridge.conf`)
2. Updates the main supervisor configuration to include this file
3. Sets up logging to the bench's log directory

After installation, you'll need to apply the supervisor changes:

```bash
bench setup supervisor
sudo supervisorctl reread
sudo supervisorctl update
```

### Standalone Installation (For Development)

For standalone development or testing:

1. Navigate to the bridge directory:
   ```bash
   cd apps/epibus/plc/bridge
   ```

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

### Test Troubleshooting

If you encounter issues with the tests:

- **ResourceWarning about unclosed files**: The logging system properly closes file handlers in the tearDown method. If you modify the logging setup, ensure proper cleanup.
  
- **JSON serialization errors**: The bridge code includes special handling for MagicMock objects that aren't JSON serializable. If you add new code that serializes objects to JSON, make sure to handle test mocks appropriately.

- **Cleanup**: Always ensure resources are properly cleaned up in the tearDown method to prevent resource leaks during testing.

## Signal Configuration

Signals are dynamically loaded from Frappe via the `get_all_signals` API endpoint:
- Configure Modbus Connections in Frappe
- Define Modbus Signals linked to those connections

## Logging

- Logs written to `plc_bridge.log`
- Console output for real-time monitoring

## Deployment Options

### Supervisor with Frappe Bench (Recommended)

When deployed as part of a Frappe bench installation, the PLC Bridge is managed by supervisor. This is the recommended approach for production environments as it:

- Ensures the bridge starts and stops with other Frappe services
- Provides automatic restart on failure
- Integrates with the bench's logging system
- Simplifies management through supervisor commands

The supervisor configuration is automatically created during installation and can be found at:
```
/home/intralogisticsuser/frappe-bench/config/supervisor/plc_bridge.conf
```

To manage the service:
```bash
# Check status
sudo supervisorctl status bench-frappe-plc-bridge

# Start the service
sudo supervisorctl start bench-frappe-plc-bridge

# Stop the service
sudo supervisorctl stop bench-frappe-plc-bridge

# Restart the service
sudo supervisorctl restart bench-frappe-plc-bridge
```

### Systemd Service (Alternative)

For standalone deployments outside of the Frappe bench, you can create a systemd service:

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

Save this to `/etc/systemd/system/plc-bridge.service` and enable it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable plc-bridge
sudo systemctl start plc-bridge
```

## Monitoring and Troubleshooting

### Checking Bridge Status in Production

To verify if the PLC Bridge is running in a production environment:

1. **Check Supervisor Status:**
   ```bash
   # Check individual process status
   sudo supervisorctl status bench-frappe-plc-bridge
   
   # Check the entire process group
   sudo supervisorctl status bench-frappe-plc:
   ```
   
   You should see output like:
   ```
   bench-frappe-plc-bridge                RUNNING   pid 12345, uptime 2 days, 3:45:12
   ```
   
   Or when checking the group:
   ```
   bench-frappe-plc:bench-frappe-plc-bridge   RUNNING   pid 12345, uptime 2 days, 3:45:12
   ```
   
   You can also use the bench command:
   ```bash
   bench supervisor status
   ```

2. **View Recent Logs:**
   ```bash
   # View the main log file
   tail -f /home/intralogisticsuser/frappe-bench/logs/plc_bridge.log
   
   # View error logs
   tail -f /home/intralogisticsuser/frappe-bench/logs/plc_bridge.error.log
   ```

3. **Verify Communication:**
   - Check for "Signal Change" entries in the logs, which indicate successful communication with PLCs
   - In Frappe, navigate to the Modbus Signals dashboard to see if values are being updated
   - Use the Frappe API to query signal values:
     ```bash
     curl -H "Authorization: token API_KEY:API_SECRET" \
          "https://your-frappe-site.com/api/resource/Modbus Signal/SIGNAL_NAME"
     ```

### Common Issues

- Verify Frappe URL and API credentials in `.env` file
- Check network connectivity to PLC devices
- Review `plc_bridge.log` for detailed errors
- Ensure Modbus devices are configured in Frappe
- Check if the PLC devices are powered on and accessible

### Restarting the Bridge

The PLC Bridge can be restarted in two ways:

#### 1. Using `bench restart` (Recommended)

The PLC Bridge is integrated with the Frappe bench workers group, so it can be restarted using the standard bench command:

```bash
# Restart all services including the PLC Bridge
bench restart
```

This ensures the bridge is restarted along with other Frappe services.

#### 2. Using supervisor directly

You can also restart the bridge directly using supervisor commands:

```bash
# Restart the bridge process
sudo supervisorctl restart frappe-bench-plc-bridge

# Restart all workers including the PLC Bridge
sudo supervisorctl restart frappe-bench-workers:
```

This gives you more fine-grained control over restarting specific processes.

After restarting, check the logs to verify it's working properly:

```bash
tail -f /home/intralogisticsuser/frappe-bench/logs/plc_bridge.log
```

You should see messages about loading signals and establishing connections to PLC devices.

## Development Notes

- Modbus communication is implemented in the `_read_signal` and `_write_signal` methods
- Signal updates are published to Frappe via the `_publish_signal_update` method
- The bridge supports multiple Modbus connections simultaneously
- Each connection has its own Modbus client
- The automatic installation process is handled by `apps/epibus/epibus/install.py`
- The supervisor configuration is created at `config/supervisor/plc_bridge.conf`

### Development Workflow

1. **Local Development:**
   - Make changes to the bridge code
   - Test locally using `./start_bridge.sh` or `python bridge.py`
   - Run the test suite with `./run_tests.sh`

2. **Deployment:**
   - For production, commit your changes to the epibus app repository
   - When the app is installed/updated, the bridge will be automatically configured
   - Apply supervisor changes with `bench setup supervisor && sudo supervisorctl reread && sudo supervisorctl update`
   - Monitor logs at `/home/intralogisticsuser/frappe-bench/logs/plc_bridge.log`

## Key Characteristics

- Integrated with Frappe bench for production deployment
- Can also run as a standalone service for development
- No Frappe runtime dependency
- Direct REST API communication
- Dynamically configured via Frappe documents
- Automatic installation and configuration