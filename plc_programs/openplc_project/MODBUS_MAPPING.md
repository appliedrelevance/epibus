# OpenPLC Intralogistics Lab - MODBUS Address Mapping

## Overview

This document provides a complete mapping of MODBUS TCP addresses used in the OpenPLC Intralogistics Learning Lab project. The system operates as a MODBUS TCP server on port 502, allowing external ERP systems to monitor and control the automation processes.

## Connection Information

- **Protocol**: MODBUS TCP
- **Port**: 502 (standard MODBUS port)
- **Unit ID**: 1
- **IP Address**: PLC IP address (configurable)
- **Max Connections**: 5 concurrent clients
- **Timeout**: 5 seconds

## Address Format

OpenPLC uses direct physical addresses that map to MODBUS registers:

- **%IX** = Input Contacts (Read-only from MODBUS client perspective)
- **%QX** = Output Coils (Read/Write from MODBUS client)
- **%MW** = Memory Words/Holding Registers (Read/Write from MODBUS client)

## Physical I/O Mapping

### Digital Inputs (%IX) - Read Only

| OpenPLC Address | Description | MODBUS Function | Notes |
|----------------|-------------|-----------------|-------|
| %IX0.0 | Emergency Stop Button | 02 - Read Discrete Inputs | Normally Closed contact |
| %IX0.1 | Manual Reset Button | 02 - Read Discrete Inputs | Momentary contact |
| %IX0.2 | Start Button | 02 - Read Discrete Inputs | Momentary contact |
| %IX0.3 | Stop Button | 02 - Read Discrete Inputs | Momentary contact |
| %IX1.0 | PE Sensor Conv1 Entry | 02 - Read Discrete Inputs | Photo-electric sensor |
| %IX1.1 | PE Sensor Conv1 Exit | 02 - Read Discrete Inputs | Photo-electric sensor |
| %IX1.2 | PE Sensor Conv2 Entry | 02 - Read Discrete Inputs | Photo-electric sensor |
| %IX1.3 | PE Sensor Conv2 Exit | 02 - Read Discrete Inputs | Photo-electric sensor |
| %IX1.4 | PE Sensor Conv3 Entry | 02 - Read Discrete Inputs | Photo-electric sensor |
| %IX1.5 | PE Sensor Conv3 Exit | 02 - Read Discrete Inputs | Photo-electric sensor |
| %IX1.6 | PE Sensor Conv4 Entry | 02 - Read Discrete Inputs | Photo-electric sensor |
| %IX1.7 | PE Sensor Conv4 Exit | 02 - Read Discrete Inputs | Photo-electric sensor |
| %IX2.0 | Robot Home Position | 02 - Read Discrete Inputs | Position feedback |
| %IX2.1 | Robot Moving | 02 - Read Discrete Inputs | Motion status |
| %IX2.2 | Robot At Conveyor | 02 - Read Discrete Inputs | Position feedback |
| %IX2.3 | Robot Gripper Open | 02 - Read Discrete Inputs | Gripper feedback |
| %IX2.4 | Robot Gripper Closed | 02 - Read Discrete Inputs | Gripper feedback |
| %IX2.5 | Robot Error Status | 02 - Read Discrete Inputs | Error signal |
| %IX3.0 | RFID Reader1 Ready | 02 - Read Discrete Inputs | Reader status |
| %IX3.1 | RFID Reader2 Ready | 02 - Read Discrete Inputs | Reader status |
| %IX3.2 | RFID Reader1 Tag Present | 02 - Read Discrete Inputs | Tag detection |
| %IX3.3 | RFID Reader2 Tag Present | 02 - Read Discrete Inputs | Tag detection |

### Digital Outputs (%QX) - Read/Write

#### System Status Outputs (0.0-0.7)

| OpenPLC Address | Description | MODBUS Function | Notes |
|----------------|-------------|-----------------|-------|
| %QX0.0 | System Running | 01/05 - Read/Write Coils | System status indicator |
| %QX0.1 | System Error | 01/05 - Read/Write Coils | Error indicator |
| %QX0.2 | Safety OK | 01/05 - Read/Write Coils | Safety status |
| %QX0.3 | Manual Mode | 01/05 - Read/Write Coils | Manual mode active |

#### Conveyor Motor Controls (1.0-1.7)

| OpenPLC Address | Description | MODBUS Function | Notes |
|----------------|-------------|-----------------|-------|
| %QX1.0 | Conveyor1 Motor | 01/05 - Read/Write Coils | Motor control |
| %QX1.1 | Conveyor2 Motor | 01/05 - Read/Write Coils | Motor control |
| %QX1.2 | Conveyor3 Motor | 01/05 - Read/Write Coils | Motor control |
| %QX1.3 | Conveyor4 Motor | 01/05 - Read/Write Coils | Motor control |

#### Robot Control Outputs (2.0-2.7)

| OpenPLC Address | Description | MODBUS Function | Notes |
|----------------|-------------|-----------------|-------|
| %QX2.0 | Robot Enable | 01/05 - Read/Write Coils | Robot enable signal |
| %QX2.1 | Robot Move To Bin | 01/05 - Read/Write Coils | Movement command |
| %QX2.2 | Robot Move To Station | 01/05 - Read/Write Coils | Movement command |
| %QX2.3 | Robot Move Home | 01/05 - Read/Write Coils | Movement command |
| %QX2.4 | Robot Gripper Open | 01/05 - Read/Write Coils | Gripper control |
| %QX2.5 | Robot Gripper Close | 01/05 - Read/Write Coils | Gripper control |
| %QX2.6 | Robot Reset | 01/05 - Read/Write Coils | Reset command |

#### Visual/Audio Indicators (3.0-3.7)

| OpenPLC Address | Description | MODBUS Function | Notes |
|----------------|-------------|-----------------|-------|
| %QX3.0 | Green Beacon | 01/05 - Read/Write Coils | Status beacon |
| %QX3.1 | Yellow Beacon | 01/05 - Read/Write Coils | Warning beacon |
| %QX3.2 | Red Beacon | 01/05 - Read/Write Coils | Alarm beacon |
| %QX3.3 | Buzzer | 01/05 - Read/Write Coils | Audio alarm |

#### RFID Reader Controls (4.0-4.7)

| OpenPLC Address | Description | MODBUS Function | Notes |
|----------------|-------------|-----------------|-------|
| %QX4.0 | RFID Reader1 Enable | 01/05 - Read/Write Coils | Reader enable |
| %QX4.1 | RFID Reader2 Enable | 01/05 - Read/Write Coils | Reader enable |
| %QX4.2 | RFID Reader1 Read | 01/05 - Read/Write Coils | Trigger read |
| %QX4.3 | RFID Reader2 Read | 01/05 - Read/Write Coils | Trigger read |

## ERP Integration Addresses

### Process Control Signals (125.0-126.7) - PLC Status to ERP

These coils provide status information from the PLC to the ERP system:

| OpenPLC Address | Description | MODBUS Coil | Function | Notes |
|----------------|-------------|-------------|----------|-------|
| %QX125.0 | PLC Cycle Stopped | 1000 | 01 - Read Coils | PLC is stopped |
| %QX125.1 | PLC Cycle Running | 1001 | 01 - Read Coils | PLC is running |
| %QX125.2 | Pick Error | 1002 | 01 - Read Coils | Pick operation error |
| %QX125.3 | Pick To Assembly In Process | 1003 | 01 - Read Coils | Assembly pick active |
| %QX125.4 | Pick To Assembly Complete | 1004 | 01 - Read Coils | Assembly pick done |
| %QX125.5 | Pick To Receiving In Process | 1005 | 01 - Read Coils | Receiving pick active |
| %QX125.6 | Pick To Receiving Complete | 1006 | 01 - Read Coils | Receiving pick done |
| %QX125.7 | Pick To Warehouse In Process | 1007 | 01 - Read Coils | Warehouse pick active |
| %QX126.0 | Pick To Warehouse Complete | 1008 | 01 - Read Coils | Warehouse pick done |

### Bin Selection Controls (250.0-251.7) - ERP Commands to PLC

These coils are written by the ERP system to control the PLC:

| OpenPLC Address | Description | MODBUS Coil | Function | Notes |
|----------------|-------------|-------------|----------|-------|
| %QX250.0 | Pick Bin 01 | 2000 | 05/15 - Write Coils | Select bin 1 for picking |
| %QX250.1 | Pick Bin 02 | 2001 | 05/15 - Write Coils | Select bin 2 for picking |
| %QX250.2 | Pick Bin 03 | 2002 | 05/15 - Write Coils | Select bin 3 for picking |
| %QX250.3 | Pick Bin 04 | 2003 | 05/15 - Write Coils | Select bin 4 for picking |
| %QX250.4 | Pick Bin 05 | 2004 | 05/15 - Write Coils | Select bin 5 for picking |
| %QX250.5 | Pick Bin 06 | 2005 | 05/15 - Write Coils | Select bin 6 for picking |
| %QX250.6 | Pick Bin 07 | 2006 | 05/15 - Write Coils | Select bin 7 for picking |
| %QX250.7 | Pick Bin 08 | 2007 | 05/15 - Write Coils | Select bin 8 for picking |
| %QX251.0 | Pick Bin 09 | 2008 | 05/15 - Write Coils | Select bin 9 for picking |
| %QX251.1 | Pick Bin 10 | 2009 | 05/15 - Write Coils | Select bin 10 for picking |
| %QX251.2 | Pick Bin 11 | 2010 | 05/15 - Write Coils | Select bin 11 for picking |
| %QX251.3 | Pick Bin 12 | 2011 | 05/15 - Write Coils | Select bin 12 for picking |

### Station Control (252.0-252.7) - ERP Commands to PLC

| OpenPLC Address | Description | MODBUS Coil | Function | Notes |
|----------------|-------------|-------------|----------|-------|
| %QX252.4 | To Receiving Station 1 | 2020 | 05/15 - Write Coils | Move to receiving |
| %QX252.5 | From Receiving Station 1 | 2021 | 05/15 - Write Coils | From receiving |
| %QX252.6 | To Assembly Station 2 | 2022 | 05/15 - Write Coils | Move to assembly |
| %QX252.7 | From Assembly Station 2 | 2023 | 05/15 - Write Coils | From assembly |

## Holding Registers (%MW) - Read/Write

### Statistics and Monitoring (100-111)

| OpenPLC Address | Description | MODBUS Register | Function | Range | Notes |
|----------------|-------------|-----------------|----------|-------|-------|
| %MW100 | Cycle Counter | 100 | 03/04 - Read/Write | 0-32767 | Main cycle counter |
| %MW101 | Pick Operations Total | 101 | 03/04 - Read/Write | 0-32767 | Total picks performed |
| %MW102 | Assembly Picks | 102 | 03/04 - Read/Write | 0-32767 | Assembly station picks |
| %MW103 | Receiving Picks | 103 | 03/04 - Read/Write | 0-32767 | Receiving station picks |
| %MW104 | Warehouse Picks | 104 | 03/04 - Read/Write | 0-32767 | Warehouse station picks |
| %MW105 | Error Count | 105 | 03/04 - Read/Write | 0-32767 | Total error count |
| %MW106 | Uptime Seconds | 106 | 03/04 - Read/Write | 0-32767 | System uptime |
| %MW107 | System Status | 107 | 03/04 - Read/Write | 0-5 | See status codes below |
| %MW108 | Current Bin Selection | 108 | 03/04 - Read/Write | 0-12 | Active bin number |
| %MW109 | Robot Position X | 109 | 03/04 - Read/Write | 0-999 | X coordinate |
| %MW110 | Robot Position Y | 110 | 03/04 - Read/Write | 0-999 | Y coordinate |
| %MW111 | Robot Position Z | 111 | 03/04 - Read/Write | 0-999 | Z coordinate |

#### System Status Codes (Register 107)

| Value | Status | Description |
|-------|--------|-------------|
| 0 | SYSTEM_STOPPED | System stopped/not running |
| 1 | SYSTEM_READY | System ready for operation |
| 2 | SYSTEM_RUNNING | System running normally |
| 3 | SYSTEM_STOPPING | System shutting down |
| 4 | SYSTEM_ERROR | System error state |
| 5 | SYSTEM_MANUAL | System in manual mode |

### RFID Data Registers (200-205)

| OpenPLC Address | Description | MODBUS Register | Function | Notes |
|----------------|-------------|-----------------|----------|-------|
| %MW200 | RFID Reader1 Tag ID (Low) | 200 | 03/04 - Read/Write | Lower 16 bits |
| %MW201 | RFID Reader1 Tag ID (High) | 201 | 03/04 - Read/Write | Upper 16 bits |
| %MW202 | RFID Reader2 Tag ID (Low) | 202 | 03/04 - Read/Write | Lower 16 bits |
| %MW203 | RFID Reader2 Tag ID (High) | 203 | 03/04 - Read/Write | Upper 16 bits |
| %MW204 | RFID Reader1 Status | 204 | 03/04 - Read/Write | See RFID status codes |
| %MW205 | RFID Reader2 Status | 205 | 03/04 - Read/Write | See RFID status codes |

#### RFID Status Codes

| Value | Status | Description |
|-------|--------|-------------|
| 0 | IDLE | Reader idle |
| 1 | READING | Reading in progress |
| 2 | VALID | Valid tag read |
| 3 | ERROR | Reader error |

### Conveyor Status Registers (300-307)

| OpenPLC Address | Description | MODBUS Register | Function | Notes |
|----------------|-------------|-----------------|----------|-------|
| %MW300 | Conveyor1 Status | 300 | 03/04 - Read/Write | See conveyor status codes |
| %MW301 | Conveyor2 Status | 301 | 03/04 - Read/Write | See conveyor status codes |
| %MW302 | Conveyor3 Status | 302 | 03/04 - Read/Write | See conveyor status codes |
| %MW303 | Conveyor4 Status | 303 | 03/04 - Read/Write | See conveyor status codes |
| %MW304 | Conveyor1 Speed | 304 | 03/04 - Read/Write | Speed in mm/min |
| %MW305 | Conveyor2 Speed | 305 | 03/04 - Read/Write | Speed in mm/min |
| %MW306 | Conveyor3 Speed | 306 | 03/04 - Read/Write | Speed in mm/min |
| %MW307 | Conveyor4 Speed | 307 | 03/04 - Read/Write | Speed in mm/min |

#### Conveyor Status Codes

| Value | Status | Description |
|-------|--------|-------------|
| 0 | STOPPED | Conveyor stopped |
| 1 | RUNNING | Conveyor running normally |
| 2 | FAULT | Conveyor fault condition |

## MODBUS Function Codes

The system supports the following standard MODBUS function codes:

| Function | Name | Description | Address Type |
|----------|------|-------------|--------------|
| 01 | Read Coils | Read output coils (%QX) | Output bits |
| 02 | Read Discrete Inputs | Read input contacts (%IX) | Input bits |
| 03 | Read Holding Registers | Read holding registers (%MW) | 16-bit registers |
| 04 | Read Input Registers | Read input registers | 16-bit registers |
| 05 | Write Single Coil | Write single output coil (%QX) | Output bit |
| 06 | Write Single Register | Write single register (%MW) | 16-bit register |
| 15 | Write Multiple Coils | Write multiple output coils (%QX) | Output bits |
| 16 | Write Multiple Registers | Write multiple registers (%MW) | 16-bit registers |

## ERP Integration Example

### Starting a Pick Operation

1. **ERP System** writes to bin selection (e.g., coil 2001 = TRUE for bin 2)
2. **ERP System** writes to station selection (e.g., coil 2020 = TRUE for receiving)
3. **PLC** detects the command and starts robot operation
4. **PLC** sets "Pick To Receiving In Process" (coil 1005 = TRUE)
5. **Robot** executes the pick and place operation
6. **PLC** sets "Pick To Receiving Complete" (coil 1006 = TRUE) for 10 seconds
7. **ERP System** reads the completion status and updates inventory

### Monitoring System Status

- **System Status**: Read register 107 to get overall system state
- **Robot Position**: Read registers 109-111 for real-time position
- **Statistics**: Read registers 100-106 for operational data
- **Error Monitoring**: Read register 105 for error count

## Safety Considerations

⚠️ **CRITICAL**: Some addresses control safety-related functions:

- **Emergency Stop** (%IX0.0): Hardware safety input - cannot be overridden via MODBUS
- **Robot Enable** (%QX2.0): Can disable robot via MODBUS, but should be used carefully
- **Safety OK** (%QX0.2): Status only - actual safety logic is hardware-based

## Client Implementation Notes

### Connection Parameters

```
IP Address: [PLC IP Address]
Port: 502
Unit ID: 1
Timeout: 5000ms
Max Retries: 3
```

### Recommended Polling Intervals

- **System Status** (Register 107): 1 second
- **Pick Completion** (Coils 1004, 1006, 1008): 500ms
- **Robot Position** (Registers 109-111): 2 seconds
- **Statistics** (Registers 100-106): 10 seconds

### Error Handling

- Always check for MODBUS exceptions
- Implement connection retry logic
- Monitor register 105 for PLC error count increases
- Check coil 1002 for pick operation errors

## Testing and Validation

### Test Sequence

1. **Connection Test**: Read register 100 (Cycle Counter)
2. **Status Test**: Read register 107 (System Status)
3. **Command Test**: Write coil 2000 (Pick Bin 01) = TRUE
4. **Response Test**: Monitor coil 1006 (Pick Complete)
5. **Position Test**: Read registers 109-111 during operation

### Expected Responses

- **System Ready**: Register 107 = 1
- **Pick Operation**: Coils 1003/1005/1007 = TRUE during operation
- **Pick Complete**: Coils 1004/1006/1008 = TRUE for 10 seconds
- **Position Updates**: Registers 109-111 change during robot movement

---

**Note**: This mapping is specific to the OpenPLC implementation and may differ from the original CODESYS project due to platform differences and OpenPLC's addressing scheme.