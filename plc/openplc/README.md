# OpenPLC Simulator and Examples

This directory contains simulator files and examples for working with OpenPLC in the Epibus application. These files serve as reference implementations and resources for developers.

## Contents

### Python SubModule (PSM) Files

- `beachside_psm.py` - Simulation implementation for the Beachside scenario
- `intralogistics_psm.py` - Simulation implementation for the Intralogistics scenario

### Diagnostic Tools

- `modbus_client.py` - Command-line tool for testing Modbus TCP connections and commands

### Test Files

- `test_modbus_tcp.py` - Tests basic Modbus TCP connectivity
- `test_beachside_psm.py` - Tests the Beachside PSM implementation

### Configuration Examples

- `US15-B10-B1-PLC.json` - Example PLC configuration file

## Usage

These files are primarily for reference and testing purposes. They demonstrate how to:

1. Implement Python SubModules for OpenPLC
2. Test Modbus TCP connections
3. Simulate PLC behavior for development and testing

## Deployment

In a production environment, PSM files would typically be deployed to the OpenPLC server. The `modbus_client.py` tool can be used for diagnostics in any environment.
