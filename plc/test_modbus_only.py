#!/usr/bin/env python3
"""
Test script to diagnose communication with OpenPLC using only Modbus TCP.
This script doesn't rely on the PSM module and can be run on the client.
It simulates a robot moving items and waits for the correct inputs from the simulator
before proceeding with the next tests.
"""

from pymodbus.client import ModbusTcpClient
import logging
import time
import sys

# Configure logging
logging.basicConfig(format='%(levelname)s: %(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

# OpenPLC uses a specific addressing scheme for Modbus:
# For coils (digital outputs):
# %QX0.0 = address 0, %QX0.1 = address 1, etc.
# For discrete inputs (digital inputs):
# %IX0.0 = address 0, %IX0.1 = address 1, etc.
# For holding registers (analog outputs):
# %QW0 = address 0, %QW1 = address 1, etc.

# Constants from beachside_psm.py - converted to OpenPLC Modbus addresses
BIN_ADDRESSES = {
    1: 11,  # QX1.3 - PICK_BIN_01 (8 bits per byte, so 1*8+3 = 11)
    2: 12,  # QX1.4 - PICK_BIN_02 (8 bits per byte, so 1*8+4 = 12)
    3: 13,  # QX1.5 - PICK_BIN_03 (8 bits per byte, so 1*8+5 = 13)
    4: 14,  # QX1.6 - PICK_BIN_04 (8 bits per byte, so 1*8+6 = 14)
    5: 15,  # QX1.7 - PICK_BIN_05 (8 bits per byte, so 1*8+7 = 15)
    6: 16,  # QX2.0 - PICK_BIN_06 (8 bits per byte, so 2*8+0 = 16)
    7: 17,  # QX2.1 - PICK_BIN_07 (8 bits per byte, so 2*8+1 = 17)
    8: 18,  # QX2.2 - PICK_BIN_08 (8 bits per byte, so 2*8+2 = 18)
    9: 19,  # QX2.3 - PICK_BIN_09 (8 bits per byte, so 2*8+3 = 19)
    10: 20,  # QX2.4 - PICK_BIN_10 (8 bits per byte, so 2*8+4 = 20)
    11: 21,  # QX2.5 - PICK_BIN_11 (8 bits per byte, so 2*8+5 = 21)
    12: 22  # QX2.6 - PICK_BIN_12 (8 bits per byte, so 2*8+6 = 22)
}

# MODBUS Signal Addresses (converted from beachside_psm.py to OpenPLC Modbus addresses)
SIGNALS = {
    # Input signals (IX) - From PLC to ERP
    "PLC_CYCLE_RUNNING": 1,      # IX0.1 (0*8+1 = 1)
    "PICK_ERROR": 2,             # IX0.2 (0*8+2 = 2)
    "PICK_TO_ASSEMBLY_IN_PROCESS": 3,  # IX0.3 (0*8+3 = 3)
    "PICK_TO_ASSEMBLY_COMPLETE": 4,    # IX0.4 (0*8+4 = 4)
    "PICK_TO_RECEIVING_IN_PROCESS": 5,  # IX0.5 (0*8+5 = 5)
    "PICK_TO_RECEIVING_COMPLETE": 6,   # IX0.6 (0*8+6 = 6)
    "PICK_TO_STORAGE_IN_PROCESS": 7,   # IX0.7 (0*8+7 = 7)
    "PICK_TO_STORAGE_COMPLETE": 8,     # IX1.0 (1*8+0 = 8)
    "R1_CONV_2_BIN_PRESENT": 9,  # IX1.1 (1*8+1 = 9)
    "R3_CONV_4_BIN_PRESENT": 10,  # IX1.2 (1*8+2 = 10)

    # Output signals (QX) - From ERP to PLC
    "TO_RECEIVING_STA_1": 32,     # QX4.0 (4*8+0 = 32)
    "FROM_RECEIVING": 33,         # QX4.1 (4*8+1 = 33)
    "TO_ASSEMBLY_STA_1": 34,      # QX4.2 (4*8+2 = 34)
    "FROM_ASSEMBLY": 35           # QX4.3 (4*8+3 = 35)
}

# Command register
COMMAND_REGISTER = 0  # MW0 - Memory Word 0 (first holding register)

# Command values
CMD_START_CYCLE = 1
CMD_STOP_CYCLE = 2
CMD_CLEAR_ERROR = 3

# Test configuration
HOST = 'openplc'  # OpenPLC simulator hostname
PORT = 502        # Default Modbus TCP port
TIMEOUT = 10      # Default timeout for operations (seconds)

# Operation types
OPERATION_TYPES = {
    "TO_RECEIVING": {
        "station_signal": "TO_RECEIVING_STA_1",
        "in_process_signal": "PICK_TO_RECEIVING_IN_PROCESS",
        "complete_signal": "PICK_TO_RECEIVING_COMPLETE",
        "description": "Storage to Receiving"
    },
    "TO_ASSEMBLY": {
        "station_signal": "TO_ASSEMBLY_STA_1",
        "in_process_signal": "PICK_TO_ASSEMBLY_IN_PROCESS",
        "complete_signal": "PICK_TO_ASSEMBLY_COMPLETE",
        "description": "Storage to Assembly"
    },
    "FROM_RECEIVING": {
        "station_signal": "FROM_RECEIVING",
        "in_process_signal": "PICK_TO_STORAGE_IN_PROCESS",
        "complete_signal": "PICK_TO_STORAGE_COMPLETE",
        "description": "Receiving to Storage"
    },
    "FROM_ASSEMBLY": {
        "station_signal": "FROM_ASSEMBLY",
        "in_process_signal": "PICK_TO_STORAGE_IN_PROCESS",
        "complete_signal": "PICK_TO_STORAGE_COMPLETE",
        "description": "Assembly to Storage"
    }
}


def connect_to_plc():
    """Connect to the PLC and return the client"""
    log.info(f"🔌 Connecting to OpenPLC at {HOST}:{PORT}...")

    # Create client with appropriate configuration
    client = ModbusTcpClient(
        host=HOST,
        port=PORT,
        timeout=5,  # Increase timeout for better reliability
    )
    # Set the number of retries
    client.retries = 3

    connection = client.connect()
    if connection:
        log.info("✅ Connected to OpenPLC")
        return client
    else:
        log.error("❌ Failed to connect to OpenPLC")
        return None


def read_signal(client, signal_name, is_input=True):
    """Read a specific signal and return its value"""
    try:
        address = SIGNALS[signal_name]
        if is_input:
            result = client.read_discrete_inputs(address=address, count=1)
        else:
            result = client.read_coils(address=address, count=1)

        if hasattr(result, 'bits'):
            return result.bits[0]
        return None
    except Exception as e:
        log.error(f"❌ Error reading {signal_name}: {str(e)}")
        return None


def read_all_signals(client):
    """Read all signals and print their values"""
    print("\n📊 Current Signal States:")
    print("=" * 40)

    # Read input signals
    print("Input Signals (From PLC to ERP):")
    for name, address in SIGNALS.items():
        if name in ["TO_RECEIVING_STA_1", "FROM_RECEIVING", "TO_ASSEMBLY_STA_1", "FROM_ASSEMBLY"]:
            continue  # Skip output signals
        try:
            result = client.read_discrete_inputs(address=address, count=1)
            if hasattr(result, 'bits'):
                print(f"  {name}: {result.bits[0]}")
            else:
                print(f"  {name}: Failed to read")
        except Exception as e:
            print(f"  {name}: Error - {str(e)}")

    # Read output signals
    print("\nOutput Signals (From ERP to PLC):")
    for name in ["TO_RECEIVING_STA_1", "FROM_RECEIVING", "TO_ASSEMBLY_STA_1", "FROM_ASSEMBLY"]:
        try:
            address = SIGNALS[name]
            result = client.read_coils(address=address, count=1)
            if hasattr(result, 'bits'):
                print(f"  {name}: {result.bits[0]}")
            else:
                print(f"  {name}: Failed to read")
        except Exception as e:
            print(f"  {name}: Error - {str(e)}")

    # Read bin selections
    print("\nBin Selections:")
    for bin_num, address in BIN_ADDRESSES.items():
        try:
            result = client.read_coils(address=address, count=1)
            if hasattr(result, 'bits'):
                print(f"  Bin {bin_num}: {result.bits[0]}")
            else:
                print(f"  Bin {bin_num}: Failed to read")
        except Exception as e:
            print(f"  Bin {bin_num}: Error - {str(e)}")

    # Read command register
    try:
        result = client.read_holding_registers(
            address=COMMAND_REGISTER, count=1)
        if hasattr(result, 'registers'):
            print(f"\nCommand Register (MW0): {result.registers[0]}")
        else:
            print("\nCommand Register (MW0): Failed to read")
    except Exception as e:
        print(f"\nCommand Register (MW0): Error - {str(e)}")

    print("=" * 40)


def write_and_verify_coil(client, address, value, description):
    """Write a value to a coil and verify it was set correctly"""
    try:
        # Write the value
        result = client.write_coil(address=address, value=value)
        if not result:
            log.error(
                f"❌ Failed to write {value} to {description} (address {address})")
            return False

        # Read back the value to verify
        read_result = client.read_coils(address=address, count=1)
        if not hasattr(read_result, 'bits'):
            log.error(
                f"❌ Failed to read back {description} (address {address})")
            return False

        read_value = read_result.bits[0]
        if read_value == value:
            log.info(
                f"✅ Successfully wrote and verified {value} to {description} (address {address})")
            return True
        else:
            log.error(
                f"❌ Verification failed for {description} (address {address}): wrote {value}, read back {read_value}")
            return False
    except Exception as e:
        log.error(
            f"❌ Error writing/reading {description} (address {address}): {str(e)}")
        return False


def write_and_verify_register(client, address, value, description):
    """Write a value to a register and verify it was set correctly"""
    try:
        # Write the value
        result = client.write_register(address=address, value=value)
        if not result:
            log.error(
                f"❌ Failed to write {value} to {description} (address {address})")
            return False

        # Read back the value to verify
        read_result = client.read_holding_registers(address=address, count=1)
        if not hasattr(read_result, 'registers'):
            log.error(
                f"❌ Failed to read back {description} (address {address})")
            return False

        read_value = read_result.registers[0]
        if read_value == value:
            log.info(
                f"✅ Successfully wrote and verified {value} to {description} (address {address})")
            return True
        else:
            log.error(
                f"❌ Verification failed for {description} (address {address}): wrote {value}, read back {read_value}")
            return False
    except Exception as e:
        log.error(
            f"❌ Error writing/reading {description} (address {address}): {str(e)}")
        return False


def wait_for_signal(client, signal_name, expected_value=True, timeout=TIMEOUT, is_input=True, poll_interval=0.2):
    """Wait for a signal to reach the expected value with timeout"""
    log.info(
        f"⏳ Waiting for {signal_name} to be {expected_value} (timeout: {timeout}s)...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        value = read_signal(client, signal_name, is_input)

        if value == expected_value:
            log.info(f"✅ Signal {signal_name} is now {expected_value}")
            return True

        # Check for error condition
        if signal_name != "PICK_ERROR" and read_signal(client, "PICK_ERROR", True):
            log.error(f"❌ Error detected while waiting for {signal_name}")
            return False

        time.sleep(poll_interval)

    log.error(f"⏰ Timeout waiting for {signal_name} to be {expected_value}")
    return False


def execute_bin_operation(client, bin_num, operation_type):
    """Execute a complete bin operation with proper signal handling and waiting"""
    operation_info = OPERATION_TYPES[operation_type]
    station_signal = operation_info["station_signal"]
    in_process_signal = operation_info["in_process_signal"]
    complete_signal = operation_info["complete_signal"]
    description = operation_info["description"]

    log.info(f"\n🔄 Starting operation: Bin {bin_num} - {description}")

    # Step 1: Set bin selection and station signal
    log.info(f"📝 Setting bin {bin_num} and {station_signal}...")
    if not write_and_verify_coil(client, BIN_ADDRESSES[bin_num], True, f"Bin {bin_num}"):
        return False

    if not write_and_verify_coil(client, SIGNALS[station_signal], True, station_signal):
        # Clean up bin selection if station signal fails
        write_and_verify_coil(
            client, BIN_ADDRESSES[bin_num], False, f"Bin {bin_num}")
        return False

    # Step 2: Wait for in-process signal or error
    log.info(f"⏳ Waiting for operation to start...")
    if not wait_for_signal(client, in_process_signal, True, TIMEOUT, True):
        if read_signal(client, "PICK_ERROR", True):
            log.error("❌ Error detected during operation")
        else:
            log.error("❌ Operation did not start within timeout period")

        # Clean up signals
        write_and_verify_coil(
            client, BIN_ADDRESSES[bin_num], False, f"Bin {bin_num}")
        write_and_verify_coil(
            client, SIGNALS[station_signal], False, station_signal)
        return False

    # Step 3: Reset bin selection and station signal
    log.info(f"📝 Resetting bin {bin_num} and {station_signal}...")
    write_and_verify_coil(
        client, BIN_ADDRESSES[bin_num], False, f"Bin {bin_num}")
    write_and_verify_coil(
        client, SIGNALS[station_signal], False, station_signal)

    # Step 4: Wait for operation to complete or error
    log.info(f"⏳ Waiting for operation to complete...")
    success = wait_for_signal(client, complete_signal, True, TIMEOUT, True)

    if success:
        log.info(
            f"✅ Operation completed successfully: Bin {bin_num} - {description}")
    else:
        if read_signal(client, "PICK_ERROR", True):
            log.error("❌ Error detected during operation")
        else:
            log.error("❌ Operation did not complete within timeout period")

    return success


def test_command_register(client):
    """Test the command register"""
    log.info("\n🧪 Testing command register (MW0)...")

    # Read initial state
    read_all_signals(client)

    # Test start cycle command
    log.info("\n📝 Sending START CYCLE command (1)...")
    write_and_verify_register(client, COMMAND_REGISTER,
                              CMD_START_CYCLE, "Command Register (START CYCLE)")

    # Wait for PLC_CYCLE_RUNNING to become true
    wait_for_signal(client, "PLC_CYCLE_RUNNING", True, TIMEOUT, True)
    read_all_signals(client)

    # Test stop cycle command
    log.info("\n📝 Sending STOP CYCLE command (2)...")
    write_and_verify_register(client, COMMAND_REGISTER,
                              CMD_STOP_CYCLE, "Command Register (STOP CYCLE)")

    # Wait for PLC_CYCLE_RUNNING to become false
    wait_for_signal(client, "PLC_CYCLE_RUNNING", False, TIMEOUT, True)
    read_all_signals(client)


def test_bin_selection(client):
    """Test bin selection"""
    log.info("\n🧪 Testing bin selection...")

    # Read initial state
    read_all_signals(client)

    # Test selecting bin 1
    log.info("\n📝 Selecting bin 1...")
    write_and_verify_coil(client, BIN_ADDRESSES[1], True, "Bin 1")
    time.sleep(1)  # Brief pause to let the PLC register the change
    read_all_signals(client)

    # Test deselecting bin 1
    log.info("\n📝 Deselecting bin 1...")
    write_and_verify_coil(client, BIN_ADDRESSES[1], False, "Bin 1")
    time.sleep(1)  # Brief pause to let the PLC register the change
    read_all_signals(client)


def test_station_selection(client):
    """Test station selection"""
    log.info("\n🧪 Testing station selection...")

    # Read initial state
    read_all_signals(client)

    # Test setting TO_RECEIVING_STA_1
    log.info("\n📝 Setting TO_RECEIVING_STA_1...")
    write_and_verify_coil(
        client, SIGNALS["TO_RECEIVING_STA_1"], True, "TO_RECEIVING_STA_1")
    time.sleep(1)  # Brief pause to let the PLC register the change
    read_all_signals(client)

    # Test clearing TO_RECEIVING_STA_1
    log.info("\n📝 Clearing TO_RECEIVING_STA_1...")
    write_and_verify_coil(
        client, SIGNALS["TO_RECEIVING_STA_1"], False, "TO_RECEIVING_STA_1")
    time.sleep(1)  # Brief pause to let the PLC register the change
    read_all_signals(client)


def test_single_bin_operation(client, bin_num, operation_type):
    """Test a single bin operation with proper signal handling"""
    log.info(f"\n🧪 Testing bin {bin_num} {operation_type} operation...")

    # Execute the operation
    success = execute_bin_operation(client, bin_num, operation_type)

    # Read final state
    read_all_signals(client)

    return success


def test_combined_operation(client):
    """Test combined bin and station operations with proper waiting for signals"""
    log.info("\n🧪 Testing combined bin and station operations...")

    # Read initial state
    read_all_signals(client)

    # Start the PLC cycle
    log.info("\n📝 Starting PLC cycle...")
    write_and_verify_register(client, COMMAND_REGISTER,
                              CMD_START_CYCLE, "Command Register (START CYCLE)")

    # Wait for PLC_CYCLE_RUNNING to become true
    if not wait_for_signal(client, "PLC_CYCLE_RUNNING", True, TIMEOUT, True):
        log.error("❌ Failed to start PLC cycle")
        return False

    read_all_signals(client)

    # Test bin 1 to receiving
    success = test_single_bin_operation(client, 1, "TO_RECEIVING")
    if not success:
        log.error("❌ Bin 1 to receiving operation failed")

    # Test bin 2 to assembly
    success = test_single_bin_operation(client, 2, "TO_ASSEMBLY")
    if not success:
        log.error("❌ Bin 2 to assembly operation failed")

    # Stop the PLC cycle
    log.info("\n📝 Stopping PLC cycle...")
    write_and_verify_register(client, COMMAND_REGISTER,
                              CMD_STOP_CYCLE, "Command Register (STOP CYCLE)")

    # Wait for PLC_CYCLE_RUNNING to become false
    wait_for_signal(client, "PLC_CYCLE_RUNNING", False, TIMEOUT, True)
    read_all_signals(client)

    return True


def test_all_bin_operations(client):
    """Test all bins with all station operations"""
    log.info("\n🧪 Testing all bin operations...")

    # Start the PLC cycle if not already running
    if not read_signal(client, "PLC_CYCLE_RUNNING", True):
        log.info("\n📝 Starting PLC cycle...")
        write_and_verify_register(client, COMMAND_REGISTER,
                                  CMD_START_CYCLE, "Command Register (START CYCLE)")

        # Wait for PLC_CYCLE_RUNNING to become true
        if not wait_for_signal(client, "PLC_CYCLE_RUNNING", True, TIMEOUT, True):
            log.error("❌ Failed to start PLC cycle")
            return False

    # Test bins 1-3 to receiving
    for bin_num in range(1, 4):
        success = test_single_bin_operation(client, bin_num, "TO_RECEIVING")
        if not success:
            log.error(f"❌ Bin {bin_num} to receiving operation failed")

    # Test bins 4-6 to assembly
    for bin_num in range(4, 7):
        success = test_single_bin_operation(client, bin_num, "TO_ASSEMBLY")
        if not success:
            log.error(f"❌ Bin {bin_num} to assembly operation failed")

    return True


def run_diagnostic():
    """Run diagnostic tests on the OpenPLC"""
    client = connect_to_plc()
    if not client:
        log.error("❌ Cannot proceed with diagnostics without connection to PLC")
        return False

    try:
        # Read initial state
        log.info("\n🔍 Reading initial state...")
        read_all_signals(client)

        # Test command register
        test_command_register(client)

        # Test bin selection
        test_bin_selection(client)

        # Test station selection
        test_station_selection(client)

        # Test combined operation with proper signal waiting
        test_combined_operation(client)

        # Test all bin operations in sequence
        log.info("\n🧪 Testing all bin operations in sequence...")
        test_all_bin_operations(client)

        log.info("\n✅ Diagnostic tests completed")
        return True

    except Exception as e:
        log.error(f"❌ Error during diagnostic: {str(e)}")
        return False

    finally:
        # Always close the connection
        if client:
            client.close()
            log.info("\n👋 Connection closed")


if __name__ == "__main__":
    log.info("🧪 Starting OpenPLC Modbus diagnostic...")
    run_diagnostic()
