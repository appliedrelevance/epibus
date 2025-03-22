# Modbus Troubleshooting Guide

This guide provides instructions for troubleshooting issues with Modbus connections and signals in the Epibus application.

## Issue: Null Values for Modbus Signals

If you're experiencing null values for Modbus signals in a device (like US15-B10-B1), the following scripts can help diagnose and fix the issue.

## Comprehensive Troubleshooting Script

For a complete troubleshooting process, you can use the comprehensive troubleshooting script that runs all the diagnostic and fix scripts in sequence:

```bash
bench execute epibus.epibus.troubleshoot_modbus.run_all --args "US15-B10-B1"
```

This script will:

1. Check the database values for Modbus signals
2. Run the diagnostic script to test the Modbus connection
3. Run the fix script to attempt to resolve the issue
4. Verify the fix by checking if the signals now have values

The results will be saved to a timestamped log file in the `logs` directory.

## Individual Troubleshooting Scripts

If you prefer to run the scripts individually, you can use the following:

### 1. Diagnostic Script

The diagnostic script checks the Modbus connection and signal values to help identify the root cause of the issue.

```bash
bench execute epibus.epibus.debug_modbus_connection.debug_device --args "US15-B10-B1"
```

This script will:

- Test the direct connection to the Modbus device
- Test basic Modbus functions (read coils, discrete inputs, holding registers, input registers)
- Check each signal in the device
- Test the warehouse_dashboard.get_modbus_data function

The results will be logged to the Frappe error log.

### 2. Database Check Script

This script checks the Modbus signal values directly in the database to determine if the issue is with the database values or with the communication to the PLC.

```bash
bench execute epibus.epibus.check_modbus_db_values.check_device_db_values --args "US15-B10-B1"
```

This script will:

- Check the database values for each signal
- Check if the required fields exist in the DocType definition
- Test the warehouse_dashboard.get_modbus_data function

### 3. Fix Script

The fix script attempts to resolve the issue by reading the signal values directly from the Modbus device and updating the database.

```bash
bench execute epibus.epibus.fix_modbus_signals.fix_device_signals --args "US15-B10-B1"
```

This script will:

- Test the connection to the Modbus device
- Read each signal directly from the device
- Update the database with the read values
- Verify the fix by checking the warehouse_dashboard.get_modbus_data function

## Warehouse Dashboard Patch

A patch has been applied to the warehouse_dashboard.py file to fix the issue with null values. The patch:

1. Tries to read the signal value directly from the Modbus device if the database values are null
2. Updates the database with the read values
3. Adds better error handling and logging

## Common Issues and Solutions

### 1. Connection Issues

If the connection to the Modbus device fails:

- Check if the device is powered on and connected to the network
- Verify the host and port settings in the Modbus Connection document
- Try using an IP address instead of a hostname if DNS resolution is an issue
- Check if there are any firewalls blocking the connection

### 2. Signal Value Issues

If the signal values are null:

- Check if the signal types and addresses are correct
- Verify that the PLC is configured to expose the signals at the specified addresses
- Try reading the signals directly using the fix script
- Check if the database fields for storing the values exist and are properly defined

### 3. DocType Definition Issues

If there are issues with the DocType definition:

- Check if the required fields (digital_value, float_value) exist in the Modbus Signal DocType
- If fields are missing, they can be added using the Frappe Customize Form tool
- Ensure that the field types match the expected value types (Check for digital_value, Float for float_value)

## Logs

All scripts log their output to the Frappe error log. You can view the logs using:

```bash
bench --site site1.local get-frappe-error-log
```

Or by checking the log files directly:

```bash
cat frappe-bench/logs/frappe.log
```
