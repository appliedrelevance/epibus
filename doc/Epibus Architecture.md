# EpiBus Architecture Documentation

## Overview

EpiBus provides integration between ERPNext's document events and MODBUS TCP devices through a system of coordinated components. This document outlines the relationships and interactions between these components.

## Component Relationships

```mermaid
classDiagram
    class ModbusConnection {
        +String device_name
        +String device_type
        +String host
        +Int port
        +Boolean enabled
        +List~ModbusSignal~ signals
        +test_connection()
        +read_signal()
        +write_signal()
    }

    class ModbusSignal {
        +String signal_name
        +String signal_type
        +Int modbus_address
        +String plc_address
        +Boolean boolean_value
        +Float value
        +validate()
        +toggle_location_pin()
    }

    class ModbusAction {
        +String action_name
        +String description
        +Link~ModbusConnection~ device
        +Link~ModbusSignal~ signal
        +Link~ServerScript~ server_script
        +List~ModbusParameter~ parameters
        +execute_script()
    }

    class ServerScript {
        +String script_type
        +String doctype_event
        +String script
        +Boolean disabled
        +execute_doc()
        +execute_scheduled_method()
    }

    ModbusConnection "1" *-- "many" ModbusSignal : contains
    ModbusAction "many" --> "1" ModbusConnection : references
    ModbusAction "many" --> "1" ModbusSignal : controls
    ModbusAction "many" --> "1" ServerScript : executes
```

## Event Flow - Document Triggered Action

The following diagram shows how a Frappe document event flows through the system to trigger a MODBUS action:

```mermaid
sequenceDiagram
    participant Doc as Frappe Document
    participant Script as Server Script
    participant Action as Modbus Action
    participant Signal as Modbus Signal
    participant Device as Modbus Connection
    participant PLC as Modbus Connection

    Doc->>Script: Document Event (e.g. on_submit)
    Script->>Action: execute_script()
    Action->>Signal: get signal details
    Action->>Device: get device connection
    Device->>PLC: write_signal()/read_signal()
    PLC-->>Device: response
    Device-->>Signal: update value
    Signal-->>Action: return result
    Action-->>Script: execution complete
    Script-->>Doc: event handling complete
```

## Scheduler Flow - Time Triggered Action

For scheduled operations, the flow is slightly different:

```mermaid
sequenceDiagram
    participant Scheduler as Frappe Scheduler
    participant Script as Server Script
    participant Action as Modbus Action
    participant Signal as Modbus Signal
    participant Device as Modbus Connection
    participant PLC as Modbus Connection

    Scheduler->>Script: execute_scheduled_method()
    Script->>Action: execute_script()
    Action->>Signal: get signal details
    Action->>Device: get device connection
    Device->>PLC: read_signal()
    PLC-->>Device: response
    Device-->>Signal: update value
    Signal-->>Action: return result
    Action-->>Script: execution complete
    Script-->>Scheduler: job complete
```

## Key Concepts

1. **ModbusConnection**: Represents a physical MODBUS TCP device with connection details and signal definitions
2. **ModbusSignal**: Defines a specific I/O point on a Modbus Connection with addressing and type information
3. **ModbusAction**: Links Frappe events to MODBUS operations through configurable server scripts
4. **ServerScript**: Contains the Python code that defines the logic for how document events translate to MODBUS operations

## Usage Examples

### Document Event Handler

```python
# Server Script for Stock Entry submission
if doc.docstatus == 1:  # On Submit
    modbus_context = frappe.flags.modbus_context
    signal = modbus_context.get("signal")

    # Toggle output based on warehouse
    if "Bin 001" in [item.s_warehouse for item in doc.items]:
        signal.toggle_location_pin()
```

### Scheduled Reading

```python
# Server Script for periodic monitoring
modbus_context = frappe.flags.modbus_context
signal = modbus_context.get("signal")
device = modbus_context.get("device")

# Read current value
value = device.read_signal(signal)

# Create log entry
frappe.get_doc({
    "doctype": "Modbus Log",
    "signal": signal.name,
    "value": value,
    "timestamp": frappe.utils.now()
}).insert()
```
