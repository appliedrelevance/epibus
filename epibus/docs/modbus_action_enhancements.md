# Modbus Action Enhancements

This document describes the enhancements made to the Modbus Action doctype to support more sophisticated condition handling and improved error recovery.

## Overview of Changes

1. **Added Direct Signal Link**: Modbus Actions can now be directly linked to a specific signal rather than just the connection.

2. **Enhanced Condition Handling**: Added support for different condition types:

   - Any Change: Trigger on any signal value change
   - Equals: Trigger when the signal value equals a specific value
   - Greater Than: Trigger when the signal value is greater than a specific value
   - Less Than: Trigger when the signal value is less than a specific value

3. **Improved Context**: The context provided to server scripts now includes:

   - The Modbus Action document
   - The Modbus Connection document
   - The Modbus Signal document
   - The signal value
   - Parameters from the Modbus Action
   - Logger instance for direct logging

4. **Enhanced Error Handling**: Improved error logging and recovery:
   - Detailed error logging with stack traces
   - Error events recorded in the Modbus Event log
   - Better error messages for debugging

## Implementation Details

### 1. Modbus Action Doctype Changes

Added new fields to the Modbus Action doctype:

- `signal`: Link to a Modbus Signal
- `signal_condition`: Select field with options "Any Change", "Equals", "Greater Than", "Less Than"
- `signal_value`: Data field to specify the value for the condition

### 2. PLCRedisClient Changes

Enhanced the `_process_signal_actions` method to:

- Find actions linked to the signal that changed
- Evaluate the condition based on the signal value
- Execute the action only if the condition is met

Enhanced the `execute_action` function to:

- Provide a richer context to the server script
- Improve error handling and logging
- Record action execution in the Modbus Event log

## Testing

Two test scripts have been provided to verify the changes:

### 1. Test Modbus Action Conditions

This script tests the condition handling logic by creating test actions with different conditions and verifying that they are triggered correctly.

To run the test:

```bash
cd /workspace/development/frappe-bench
bench execute epibus.tests.test_modbus_action_conditions.run_tests
```

### 2. Test Signal Update

This script simulates signal updates from the PLC bridge and verifies that the signal update handling works correctly.

To run the test:

```bash
cd /workspace/development/frappe-bench
bench execute epibus.tests.test_signal_update.run_tests
```

## Usage Examples

### Example 1: Toggle a signal when another signal changes

```python
# Server Script: Toggle Signal
import frappe

def execute():
    # Get context
    context = frappe.flags.modbus_context
    signal = context["signal"]
    value = context["value"]

    # Get the target signal from parameters
    target_signal_name = context["params"].get("target_signal")
    if not target_signal_name:
        return {"status": "error", "message": "Target signal not specified"}

    # Get the target signal
    target_signal = frappe.get_doc("Modbus Signal", target_signal_name)

    # Toggle the target signal
    client = frappe.get_doc("PLCRedisClient").get_instance()
    client.write_signal(target_signal.name, not target_signal.digital_value)

    return {
        "status": "success",
        "message": f"Toggled signal {target_signal.name}"
    }
```

### Example 2: Log a message when a signal exceeds a threshold

```python
# Server Script: Log Threshold Exceeded
import frappe

def execute():
    # Get context
    context = frappe.flags.modbus_context
    signal = context["signal"]
    value = context["value"]
    threshold = float(context["params"].get("threshold", "0"))

    # Log the event
    frappe.log_error(
        f"Signal {signal.name} exceeded threshold: {value} > {threshold}",
        "Threshold Alert"
    )

    # Send an email alert
    frappe.sendmail(
        recipients=["admin@example.com"],
        subject=f"Signal Threshold Alert: {signal.name}",
        message=f"Signal {signal.name} has exceeded the threshold of {threshold} with value {value}."
    )

    return {
        "status": "success",
        "message": "Alert sent"
    }
```

## Conclusion

These enhancements make the Modbus Action system more powerful and flexible, allowing for more sophisticated automation scenarios while maintaining backward compatibility with existing actions.
