#!/usr/bin/env python3
"""
Diagnostic script for the Beachside PSM (Programmable State Machine).
This script performs basic operations and monitors all signals to help diagnose issues.
"""

from pymodbus.client import ModbusTcpClient
import logging
import time
import sys

# Configure logging
logging.basicConfig(format='%(levelname)s: %(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)  # Changed from DEBUG to INFO to reduce verbosity

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
    """Read a signal from the PLC"""
    if signal_name not in SIGNALS:
        print(f"❌ Unknown signal: {signal_name}")
        return None

    address = SIGNALS[signal_name]
    try:
        if is_input:
            result = client.read_discrete_inputs(address=address, count=1)
        else:
            result = client.read_coils(address=address, count=1)

        if hasattr(result, 'bits'):
            return result.bits[0]
        else:
            print(f"❌ Failed to read signal {signal_name}: {result}")
            return None
    except Exception as e:
        print(f"❌ Error reading signal {signal_name}: {str(e)}")
        return None


def write_signal(client, signal_name, value):
    """Write a value to a signal on the PLC"""
    if signal_name not in SIGNALS:
        print(f"❌ Unknown signal: {signal_name}")
        return False

    address = SIGNALS[signal_name]
    try:
        result = client.write_coil(address=address, value=value)
        if result:
            return True
        else:
            print(f"❌ Failed to write signal {signal_name}")
            return False
    except Exception as e:
        print(f"❌ Error writing signal {signal_name}: {str(e)}")
        return False


def select_bin(client, bin_number):
    """Select a bin by setting its coil"""
    if bin_number not in BIN_ADDRESSES:
        print(f"❌ Invalid bin number: {bin_number}")
        return False

    address = BIN_ADDRESSES[bin_number]
    try:
        result = client.write_coil(address=address, value=True)
        if result:
            print(f"✅ Selected bin {bin_number}")
            return True
        else:
            print(f"❌ Failed to select bin {bin_number}")
            return False
    except Exception as e:
        print(f"❌ Error selecting bin {bin_number}: {str(e)}")
        return False


def deselect_bin(client, bin_number):
    """Deselect a bin by clearing its coil"""
    if bin_number not in BIN_ADDRESSES:
        print(f"❌ Invalid bin number: {bin_number}")
        return False

    address = BIN_ADDRESSES[bin_number]
    try:
        result = client.write_coil(address=address, value=False)
        if result:
            print(f"✅ Deselected bin {bin_number}")
            return True
        else:
            print(f"❌ Failed to deselect bin {bin_number}")
            return False
    except Exception as e:
        print(f"❌ Error deselecting bin {bin_number}: {str(e)}")
        return False


def send_command(client, command):
    """Send a command to the PLC via the command register"""
    log.info(f"📝 Sending command: {command}")
    try:
        result = client.write_register(address=COMMAND_REGISTER, value=command)
        if result:
            log.info(f"✅ Command {command} sent successfully")
            return True
        else:
            log.error(f"❌ Failed to send command {command}")
            return False
    except Exception as e:
        log.error(f"❌ Error sending command: {str(e)}")
        return False


def read_all_signals(client):
    """Read all signals and print their values"""
    print("\n📊 Current Signal States:")
    print("=" * 40)

    # Read input signals
    print("Input Signals (From PLC to ERP):")
    for name, address in SIGNALS.items():
        if name in ["TO_RECEIVING_STA_1", "FROM_RECEIVING", "TO_ASSEMBLY_STA_1", "FROM_ASSEMBLY"]:
            continue  # Skip output signals
        value = read_signal(client, name, is_input=True)
        print(f"  {name}: {value}")

    # Read output signals
    print("\nOutput Signals (From ERP to PLC):")
    for name in ["TO_RECEIVING_STA_1", "FROM_RECEIVING", "TO_ASSEMBLY_STA_1", "FROM_ASSEMBLY"]:
        value = read_signal(client, name, is_input=False)
        print(f"  {name}: {value}")

    # Read bin selections
    print("\nBin Selections:")
    for bin_num in range(1, 13):
        address = BIN_ADDRESSES[bin_num]
        result = client.read_coils(address=address, count=1)
        if hasattr(result, 'bits'):
            print(f"  Bin {bin_num}: {result.bits[0]}")

    # Read command register
    result = client.read_holding_registers(address=COMMAND_REGISTER, count=1)
    if hasattr(result, 'registers'):
        print(f"\nCommand Register (MW0): {result.registers[0]}")

    print("=" * 40)


def log_robot_operation(message, delay=2):
    """Log a robot operation with a delay to make it visible"""
    log.warning(f"🤖 ROBOT RUNNING: {message}")
    print(f"⏳ Waiting {delay} seconds for robot operation...")
    time.sleep(delay)
    log.warning(f"🤖 ROBOT OPERATION COMPLETE: {message}")


def run_diagnostic():
    """Run diagnostic tests on the beachside PSM"""
    client = connect_to_plc()
    if not client:
        print("❌ Cannot proceed with diagnostics without connection to PLC")
        return False

    # Track actions for summary
    actions_performed = []

    try:
        # Read initial state
        print("\n🔍 Reading initial state...")
        read_all_signals(client)
        actions_performed.append("Read initial state")

        # Start the PLC cycle
        print("\n▶️ Starting PLC cycle...")
        send_command(client, CMD_START_CYCLE)
        log_robot_operation("Starting PLC cycle")
        read_all_signals(client)
        actions_performed.append("Started PLC cycle")

        # Try a simple storage to receiving operation
        print("\n📦 Testing storage to receiving operation...")
        actions_performed.append("Tested storage to receiving operation")

        # Clear any previous signals
        print("Clearing any previous signals...")
        write_signal(client, "TO_RECEIVING_STA_1", False)
        for bin_num in range(1, 13):
            deselect_bin(client, bin_num)
        log_robot_operation("Clearing signals", delay=2)
        actions_performed.append("Cleared previous signals")

        # Select bin 1 and set TO_RECEIVING_STA_1
        print("Selecting bin 1 and setting TO_RECEIVING_STA_1...")
        select_bin(client, 1)
        write_signal(client, "TO_RECEIVING_STA_1", True)
        log_robot_operation("Moving bin 1 to receiving station", delay=3)
        actions_performed.append("Selected bin 1 and set TO_RECEIVING_STA_1")

        # Monitor signals for 30 seconds
        print("Monitoring signals for 30 seconds...")
        start_time = time.time()
        check_count = 0
        while time.time() - start_time < 30:
            read_all_signals(client)
            check_count += 1
            time.sleep(5)  # Check every 5 seconds
        actions_performed.append(
            f"Monitored signals for 30 seconds ({check_count} checks)")

        # Clean up
        print("Cleaning up...")
        deselect_bin(client, 1)
        write_signal(client, "TO_RECEIVING_STA_1", False)
        log_robot_operation("Resetting bin positions", delay=2)
        actions_performed.append(
            "Cleaned up (deselected bin 1, reset TO_RECEIVING_STA_1)")

        # Stop the PLC cycle
        print("\n⏹️ Stopping PLC cycle...")
        send_command(client, CMD_STOP_CYCLE)
        log_robot_operation("Stopping PLC cycle")
        read_all_signals(client)
        actions_performed.append("Stopped PLC cycle")

        # Print summary of actions
        print("\n📋 SUMMARY OF ACTIONS TAKEN:")
        print("=" * 40)
        for i, action in enumerate(actions_performed, 1):
            print(f"{i}. {action}")
        print("=" * 40)

        print("\n✅ Diagnostic complete")
        return True

    except Exception as e:
        print(f"❌ Error during diagnostic: {str(e)}")
        actions_performed.append(f"ERROR: {str(e)}")

        # Print summary even if there was an error
        print("\n📋 SUMMARY OF ACTIONS TAKEN (WITH ERROR):")
        print("=" * 40)
        for i, action in enumerate(actions_performed, 1):
            print(f"{i}. {action}")
        print("=" * 40)

        return False

    finally:
        # Always close the connection
        if client:
            client.close()
            print("\n👋 Connection closed")


if __name__ == "__main__":
    log.info("🧪 Starting Beachside PSM diagnostic...")
    run_diagnostic()
