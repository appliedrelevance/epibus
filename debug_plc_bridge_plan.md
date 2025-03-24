# Debug Configuration Plan for PLC Bridge

## Current Understanding

Based on the analysis of `start_plc_bridge.sh`, I need to create a VSCode launch configuration that will enable debugging of the `plc_bridge.py` script with the same parameters used in the shell script.

## Key Parameters from `start_plc_bridge.sh`

The script executes `plc_bridge.py` with these parameters:
```bash
nohup python3 "$BRIDGE_SCRIPT" --plc-host 192.168.0.11 --redis-host $REDIS_HOST --redis-port $REDIS_PORT > "$LOG_FILE" 2>&1 &
```

Where:
- `BRIDGE_SCRIPT` is `"$APP_DIR/plc/bridge/plc_bridge.py"`
- `REDIS_HOST` is `"127.0.0.1"`
- `REDIS_PORT` is `"6379"`

## Proposed Launch Configuration

Here's the launch configuration to add to `.vscode/launch.json`:

```json
{
  "name": "Debug PLC Bridge",
  "type": "python",
  "request": "launch",
  "program": "${workspaceFolder}/plc/bridge/plc_bridge.py",
  "args": [
    "--plc-host", "192.168.0.11",
    "--redis-host", "127.0.0.1",
    "--redis-port", "6379"
  ],
  "cwd": "${workspaceFolder}/plc/bridge",
  "env": {
    "PYTHONPATH": "${workspaceFolder}"
  },
  "console": "integratedTerminal",
  "justMyCode": false
}
```

## Configuration Details

1. **Program Path**: Points to the `plc_bridge.py` script
2. **Arguments**: Includes the same command-line arguments as in the shell script
3. **Working Directory**: Sets to the directory containing `plc_bridge.py`
4. **Environment Variables**: Adds the workspace folder to the Python path
5. **Console**: Uses the integrated terminal for output
6. **justMyCode**: Set to false to enable debugging of library code

## Implementation Steps

1. Switch to Code mode
2. Open `.vscode/launch.json`
3. Add the new configuration to the `configurations` array
4. Save the file
5. Test the configuration by setting breakpoints in `plc_bridge.py` and starting the debug session

## Benefits of This Approach

- Enables step-by-step debugging of the PLC Bridge code
- Matches the exact runtime environment of the shell script
- Preserves all existing launch configurations
- Allows for inspection of variables and the call stack during execution