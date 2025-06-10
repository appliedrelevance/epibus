# PLC Bridge Docker Configuration

This directory contains the Docker configuration for the PLC Bridge service, which provides real-time communication between Frappe/ERPNext and PLC devices via MODBUS TCP.

## Overview

The PLC Bridge is a standalone Python service that:
- Connects to PLC devices via MODBUS TCP
- Polls signal values at configurable intervals
- Provides real-time updates via Server-Sent Events (SSE)
- Integrates with Frappe/ERPNext for signal management and logging

## Files

- `Dockerfile` - Docker image definition for the PLC Bridge
- `bridge.py` - Main PLC Bridge application
- `config.py` - Configuration management
- `requirements.txt` - Python dependencies
- `start_bridge.sh` - Standalone startup script (for non-Docker use)
- `test_bridge.py` - Unit tests

## Docker Usage

### Building the Image

```bash
docker build -t plc-bridge .
```

### Running with Docker Compose

The PLC Bridge is designed to run as part of the frappe_docker composition. Use the provided override file:

```bash
# From the frappe_docker root directory
docker-compose -f compose.yaml -f overrides/compose.mac-m4.yaml -f overrides/compose.redis.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.openplc.yaml -f overrides/compose.plc-bridge.yaml up -d
```

### Environment Variables

Required:
- `FRAPPE_URL` - URL to the Frappe server (e.g., http://frontend:8080)
- `FRAPPE_API_KEY` - Frappe API key for authentication
- `FRAPPE_API_SECRET` - Frappe API secret for authentication

Optional:
- `PLC_POLL_INTERVAL` - Signal polling interval in seconds (default: 1.0)
- `PLC_LOG_LEVEL` - Logging level (default: INFO)
- `SSE_HOST` - SSE server bind address (default: 0.0.0.0)
- `SSE_PORT` - SSE server port (default: 7654)

### Ports

- `7654` - SSE server for real-time signal updates

### Health Check

The container includes a health check that verifies the SSE server is responding:
- Endpoint: `http://localhost:7654/signals`
- Interval: 30 seconds
- Timeout: 10 seconds
- Start period: 30 seconds

### Volumes

- `plc-bridge-logs:/app/logs` - Persistent log storage

## Integration with frappe_docker

The PLC Bridge integrates with the frappe_docker composition by:

1. **Dependencies**: Waits for the `backend` and `openplc` services to be ready
2. **Network**: Uses the same Docker network as other Frappe services
3. **Configuration**: Connects to Frappe via the internal network
4. **Data Flow**: 
   - Reads signal configurations from Frappe
   - Polls PLC devices for signal values
   - Publishes updates back to Frappe
   - Streams real-time data via SSE

## API Endpoints

The PLC Bridge exposes several HTTP endpoints:

- `GET /signals` - Get current signal values
- `POST /write_signal` - Write a value to a signal
- `GET /events` - SSE stream for real-time updates
- `GET /events/history` - Get event history
- `GET /shutdown` - Graceful shutdown

## Logging

Logs are written to:
- Container stdout/stderr (visible via `docker logs`)
- `/app/plc_bridge.log` (persistent if volume mounted)

Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Troubleshooting

### Common Issues

1. **Connection refused to Frappe**
   - Check `FRAPPE_URL` environment variable
   - Ensure Frappe backend is running and accessible
   - Verify API credentials

2. **MODBUS connection failures**
   - Check PLC device connectivity
   - Verify MODBUS TCP settings in Frappe
   - Ensure OpenPLC container is running (if using simulator)

3. **Port 7654 already in use**
   - Check for existing PLC Bridge processes
   - Use `docker ps` to see running containers
   - Stop conflicting services

### Debug Mode

To run with debug logging:

```bash
docker-compose -f compose.yaml -f overrides/compose.mac-m4.yaml -f overrides/compose.redis.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.openplc.yaml -f overrides/compose.plc-bridge.yaml up -d
docker-compose -f compose.yaml -f overrides/compose.mac-m4.yaml -f overrides/compose.redis.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.openplc.yaml -f overrides/compose.plc-bridge.yaml exec plc-bridge bash
# Inside container:
PLC_LOG_LEVEL=DEBUG python bridge.py --frappe-url "$FRAPPE_URL" --api-key "$FRAPPE_API_KEY" --api-secret "$FRAPPE_API_SECRET"
```

### Testing

Run unit tests:

```bash
docker-compose -f compose.yaml -f overrides/compose.mac-m4.yaml -f overrides/compose.redis.yaml -f overrides/compose.mariadb.yaml -f overrides/compose.openplc.yaml -f overrides/compose.plc-bridge.yaml exec plc-bridge python -m pytest test_bridge.py -v
```

## Development

For development, you can mount the source code:

```yaml
services:
  plc-bridge:
    volumes:
      - ./epibus/plc/bridge:/app
      - plc-bridge-logs:/app/logs
```

This allows live code changes without rebuilding the image.