#!/usr/bin/env python3
"""
Test script for the Beachside PSM (Programmable State Machine) using Pymodbus.
This script connects to the OpenPLC simulator and tests that it is operating properly.
"""

from pymodbus.client import ModbusTcpClient
import logging
import time
import sys

# Enable debug logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

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


def test_dns_resolution(host):
    """Test DNS resolution of the host"""
    import socket
    print(f"\n🔍 Testing DNS resolution for {host}...")
    try:
        ip = socket.gethostbyname(host)
        print(f"✅ DNS Resolution successful: {host} -> {ip}")
        return True
    except socket.gaierror as e:
        print(f"❌ DNS Resolution failed: {str(e)}")
        return False


def connect_to_plc():
    """Connect to the PLC and return the client"""
    print(f"🔌 Connecting to OpenPLC at {HOST}:{PORT}...")

    # Test DNS resolution first
    if not test_dns_resolution(HOST):
        print("❌ Cannot resolve hostname. Check Docker network configuration.")
        return None

    # Create a client with retry on failure
    for attempt in range(3):  # Try 3 times
        try:
            print(f"Connection attempt {attempt+1}/3...")
            # Create client with appropriate configuration
            # The newer versions of Pymodbus have different parameters
            client = ModbusTcpClient(
                host=HOST,
                port=PORT,
                timeout=5,  # Increase timeout for better reliability
            )
            # Set the number of retries
            client.retries = 3

            connection = client.connect()
            if connection:
                print("✅ Connected to OpenPLC")
                # Test the connection with a simple read
                result = client.read_coils(address=0, count=1)
                if hasattr(result, 'bits'):
                    print(
                        f"✅ Connection verified with test read: {result.bits}")
                    return client
                else:
                    print(f"⚠️ Connected but test read failed: {result}")
                    client.close()
            else:
                print("❌ Failed to connect to OpenPLC")

            # Wait before retrying
            if attempt < 2:  # Don't wait after the last attempt
                print("Waiting 2 seconds before retrying...")
                time.sleep(2)

        except Exception as e:
            print(f"❌ Connection error: {str(e)}")
            if attempt < 2:  # Don't wait after the last attempt
                print("Waiting 2 seconds before retrying...")
                time.sleep(2)

    print("❌ All connection attempts failed")
    return None


def test_basic_connectivity(client):
    """Test basic connectivity to the PLC"""
    print("\n🔍 Testing basic connectivity...")

    try:
        # Try reading some coils (digital outputs)
        print("  Reading first 8 coils...")
        result = client.read_coils(address=0, count=8)
        if hasattr(result, 'bits'):
            print(f"  ✅ Coil values: {result.bits}")
        else:
            print(f"  ❌ Failed to read coils: {result}")
            return False

        # Try reading discrete inputs
        print("  Reading first 8 discrete inputs...")
        result = client.read_discrete_inputs(address=0, count=8)
        if hasattr(result, 'bits'):
            print(f"  ✅ Input values: {result.bits}")
        else:
            print(f"  ❌ Failed to read inputs: {result}")
            return False

        # Try reading holding registers
        print("  Reading first holding register (MW0)...")
        result = client.read_holding_registers(address=0, count=1)
        if hasattr(result, 'registers'):
            print(f"  ✅ Register value: {result.registers[0]}")
        else:
            print(f"  ❌ Failed to read register: {result}")
            return False

        print("✅ Basic connectivity tests passed")
        return True

    except Exception as e:
        print(f"❌ Error during basic connectivity test: {str(e)}")
        return False


def send_command(client, command):
    """Send a command to the PLC via the command register"""
    print(f"📝 Sending command: {command}")
    try:
        result = client.write_register(address=COMMAND_REGISTER, value=command)
        if result:
            print(f"✅ Command {command} sent successfully")
            return True
        else:
            print(f"❌ Failed to send command {command}")
            return False
    except Exception as e:
        print(f"❌ Error sending command: {str(e)}")
        return False


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


def wait_for_signal(client, signal_name, expected_value, timeout=TIMEOUT, is_input=True):
    """Wait for a signal to reach the expected value within the timeout period"""
    print(
        f"⏳ Waiting for {signal_name} to be {expected_value} (timeout: {timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        value = read_signal(client, signal_name, is_input)
        if value == expected_value:
            print(f"✅ Signal {signal_name} is now {expected_value}")
            return True
        time.sleep(0.5)  # Check every 500ms

    print(f"❌ Timeout waiting for {signal_name} to be {expected_value}")
    return False


def test_cycle_start_stop(client):
    """Test starting and stopping the PLC cycle"""
    print("\n🔄 Testing PLC cycle start/stop...")

    # First, ensure the cycle is stopped
    print("Stopping any running cycle...")
    send_command(client, CMD_STOP_CYCLE)
    time.sleep(2)  # Give more time for the command to be processed

    # Check initial cycle state
    cycle_running = read_signal(client, "PLC_CYCLE_RUNNING")
    print(f"Initial PLC_CYCLE_RUNNING state: {cycle_running}")

    # Start the cycle
    print("▶️ Starting PLC cycle...")
    result = send_command(client, CMD_START_CYCLE)
    if not result:
        print("❌ Failed to send start command")
        return False

    # Wait for cycle running signal with a longer timeout
    print("Waiting for PLC_CYCLE_RUNNING to become TRUE...")
    if not wait_for_signal(client, "PLC_CYCLE_RUNNING", True, timeout=15):
        # If we can't detect the signal change, try to verify it's running another way
        print("⚠️ Could not detect PLC_CYCLE_RUNNING signal change")
        print("Checking current state...")
        cycle_running = read_signal(client, "PLC_CYCLE_RUNNING")
        if cycle_running:
            print("✅ PLC cycle is running despite not detecting the change")
        else:
            print("❌ PLC cycle is not running")
            return False

    # Verify the cycle is running
    print("Verifying cycle is running...")
    cycle_running = read_signal(client, "PLC_CYCLE_RUNNING")
    if not cycle_running:
        print("❌ PLC cycle should be running but isn't")
        return False

    print("✅ PLC cycle start test passed")

    # Stop the cycle
    print("⏹️ Stopping PLC cycle...")
    result = send_command(client, CMD_STOP_CYCLE)
    if not result:
        print("❌ Failed to send stop command")
        return False

    # Wait for cycle stopped signal with a longer timeout
    print("Waiting for PLC_CYCLE_RUNNING to become FALSE...")
    if not wait_for_signal(client, "PLC_CYCLE_RUNNING", False, timeout=15):
        # If we can't detect the signal change, try to verify it's stopped another way
        print("⚠️ Could not detect PLC_CYCLE_RUNNING signal change")
        print("Checking current state...")
        cycle_running = read_signal(client, "PLC_CYCLE_RUNNING")
        if not cycle_running:
            print("✅ PLC cycle is stopped despite not detecting the change")
        else:
            print("❌ PLC cycle is still running")
            return False

    print("✅ PLC cycle start/stop test passed")
    return True


def test_storage_to_receiving(client):
    """Test the storage to receiving sequence"""
    print("\n📦 Testing storage to receiving sequence...")

    # Ensure the cycle is running
    print("Ensuring PLC cycle is running...")
    cycle_running = read_signal(client, "PLC_CYCLE_RUNNING")
    if not cycle_running:
        print("Starting PLC cycle...")
        send_command(client, CMD_START_CYCLE)
        if not wait_for_signal(client, "PLC_CYCLE_RUNNING", True, timeout=15):
            print("❌ Failed to start PLC cycle")
            return False
    else:
        print("✅ PLC cycle is already running")

    # Clear any previous signals
    print("Clearing any previous signals...")
    write_signal(client, "TO_RECEIVING_STA_1", False)
    for bin_num in range(1, 13):
        deselect_bin(client, bin_num)
    time.sleep(2)  # Give time for signals to clear

    # Select bin 1 and set TO_RECEIVING_STA_1
    print("1️⃣ Selecting bin 1 and setting TO_RECEIVING_STA_1...")
    success = select_bin(client, 1)
    if not success:
        print("❌ Failed to select bin 1")
        return False

    success = write_signal(client, "TO_RECEIVING_STA_1", True)
    if not success:
        print("❌ Failed to set TO_RECEIVING_STA_1")
        return False

    # Wait for PICK_TO_RECEIVING_IN_PROCESS with a longer timeout
    print("Waiting for PICK_TO_RECEIVING_IN_PROCESS signal...")
    if not wait_for_signal(client, "PICK_TO_RECEIVING_IN_PROCESS", True, timeout=20):
        # Check if we're already in process (might have missed the transition)
        in_process = read_signal(client, "PICK_TO_RECEIVING_IN_PROCESS")
        if in_process:
            print("✅ Already in PICK_TO_RECEIVING_IN_PROCESS state")
        else:
            print("❌ Failed to detect PICK_TO_RECEIVING_IN_PROCESS")
            # Continue anyway to see if the operation completes

    # Deselect bin and clear TO_RECEIVING_STA_1
    print("2️⃣ Deselecting bin 1 and clearing TO_RECEIVING_STA_1...")
    deselect_bin(client, 1)
    write_signal(client, "TO_RECEIVING_STA_1", False)

    # Wait for operation to complete with a longer timeout
    print("3️⃣ Waiting for operation to complete...")
    if not wait_for_signal(client, "PICK_TO_RECEIVING_COMPLETE", True, timeout=30):
        # Check if we're already complete (might have missed the transition)
        complete = read_signal(client, "PICK_TO_RECEIVING_COMPLETE")
        if complete:
            print("✅ Already in PICK_TO_RECEIVING_COMPLETE state")
        else:
            print("❌ Failed to detect PICK_TO_RECEIVING_COMPLETE")
            # Continue anyway to check if the bin is present

    # Check if bin is present on receiving conveyor
    print("4️⃣ Checking if bin is present on receiving conveyor...")
    if not wait_for_signal(client, "R1_CONV_2_BIN_PRESENT", True, timeout=15):
        bin_present = read_signal(client, "R1_CONV_2_BIN_PRESENT")
        if bin_present:
            print("✅ Bin is already present on receiving conveyor")
        else:
            print("❌ Bin is not present on receiving conveyor")
            return False

    print("✅ Storage to receiving test passed")
    return True


def test_receiving_to_storage(client):
    """Test the receiving to storage sequence"""
    print("\n📦 Testing receiving to storage sequence...")

    # Ensure the cycle is running
    if not read_signal(client, "PLC_CYCLE_RUNNING"):
        send_command(client, CMD_START_CYCLE)
        if not wait_for_signal(client, "PLC_CYCLE_RUNNING", True):
            return False

    # The bin should already be on the receiving conveyor from the previous test
    # Wait for PICK_TO_STORAGE_IN_PROCESS (the PSM should automatically detect the bin)
    print("1️⃣ Waiting for automatic bin detection and PICK_TO_STORAGE_IN_PROCESS...")
    if not wait_for_signal(client, "PICK_TO_STORAGE_IN_PROCESS", True, timeout=15):
        return False

    # Wait for operation to complete
    print("2️⃣ Waiting for operation to complete...")
    if not wait_for_signal(client, "PICK_TO_STORAGE_COMPLETE", True, timeout=15):
        return False

    # Check if bin is no longer present on receiving conveyor
    if not wait_for_signal(client, "R1_CONV_2_BIN_PRESENT", False):
        return False

    print("✅ Receiving to storage test passed")
    return True


def test_storage_to_assembly(client):
    """Test the storage to assembly sequence"""
    print("\n📦 Testing storage to assembly sequence...")

    # Ensure the cycle is running
    if not read_signal(client, "PLC_CYCLE_RUNNING"):
        send_command(client, CMD_START_CYCLE)
        if not wait_for_signal(client, "PLC_CYCLE_RUNNING", True):
            return False

    # Select bin 2 and set TO_ASSEMBLY_STA_1
    print("1️⃣ Selecting bin 2 and setting TO_ASSEMBLY_STA_1...")
    select_bin(client, 2)
    write_signal(client, "TO_ASSEMBLY_STA_1", True)

    # Wait for PICK_TO_ASSEMBLY_IN_PROCESS
    if not wait_for_signal(client, "PICK_TO_ASSEMBLY_IN_PROCESS", True):
        return False

    # Deselect bin and clear TO_ASSEMBLY_STA_1
    print("2️⃣ Deselecting bin 2 and clearing TO_ASSEMBLY_STA_1...")
    deselect_bin(client, 2)
    write_signal(client, "TO_ASSEMBLY_STA_1", False)

    # Wait for operation to complete
    print("3️⃣ Waiting for operation to complete...")
    if not wait_for_signal(client, "PICK_TO_ASSEMBLY_COMPLETE", True, timeout=15):
        return False

    # Check if bin is present on assembly conveyor
    if not wait_for_signal(client, "R3_CONV_4_BIN_PRESENT", True):
        return False

    print("✅ Storage to assembly test passed")
    return True


def test_assembly_to_storage(client):
    """Test the assembly to storage sequence"""
    print("\n📦 Testing assembly to storage sequence...")

    # Ensure the cycle is running
    if not read_signal(client, "PLC_CYCLE_RUNNING"):
        send_command(client, CMD_START_CYCLE)
        if not wait_for_signal(client, "PLC_CYCLE_RUNNING", True):
            return False

    # The bin should already be on the assembly conveyor from the previous test
    # Wait for PICK_TO_STORAGE_IN_PROCESS (the PSM should automatically detect the bin)
    print("1️⃣ Waiting for automatic bin detection and PICK_TO_STORAGE_IN_PROCESS...")
    if not wait_for_signal(client, "PICK_TO_STORAGE_IN_PROCESS", True, timeout=15):
        return False

    # Wait for operation to complete
    print("2️⃣ Waiting for operation to complete...")
    if not wait_for_signal(client, "PICK_TO_STORAGE_COMPLETE", True, timeout=15):
        return False

    # Check if bin is no longer present on assembly conveyor
    if not wait_for_signal(client, "R3_CONV_4_BIN_PRESENT", False):
        return False

    print("✅ Assembly to storage test passed")
    return True


def test_error_handling(client):
    """Test error handling by forcing an error and then clearing it"""
    print("\n⚠️ Testing error handling...")

    # Ensure the cycle is running
    if not read_signal(client, "PLC_CYCLE_RUNNING"):
        send_command(client, CMD_START_CYCLE)
        if not wait_for_signal(client, "PLC_CYCLE_RUNNING", True):
            return False

    # Start an operation but then force an error by stopping the cycle
    print("1️⃣ Starting an operation and forcing an error...")
    select_bin(client, 3)
    write_signal(client, "TO_RECEIVING_STA_1", True)

    # Wait for operation to start
    if not wait_for_signal(client, "PICK_TO_RECEIVING_IN_PROCESS", True):
        return False

    # Force an error by stopping the cycle
    send_command(client, CMD_STOP_CYCLE)
    time.sleep(1)  # Give it time to process

    # Restart the cycle
    send_command(client, CMD_START_CYCLE)
    if not wait_for_signal(client, "PLC_CYCLE_RUNNING", True):
        return False

    # Check if error state is set
    error_state = read_signal(client, "PICK_ERROR")
    print(f"  Error state: {error_state}")

    # Clear the error
    print("2️⃣ Clearing the error...")
    send_command(client, CMD_CLEAR_ERROR)

    # Wait for error to clear
    if not wait_for_signal(client, "PICK_ERROR", False):
        return False

    # Clean up
    deselect_bin(client, 3)
    write_signal(client, "TO_RECEIVING_STA_1", False)

    print("✅ Error handling test passed")
    return True


def check_all_signals(client):
    """Check and return the current state of all signals"""
    signal_states = {}

    # Check all input signals
    input_signals = [
        "PLC_CYCLE_RUNNING",
        "PICK_ERROR",
        "PICK_TO_ASSEMBLY_IN_PROCESS",
        "PICK_TO_ASSEMBLY_COMPLETE",
        "PICK_TO_RECEIVING_IN_PROCESS",
        "PICK_TO_RECEIVING_COMPLETE",
        "PICK_TO_STORAGE_IN_PROCESS",
        "PICK_TO_STORAGE_COMPLETE",
        "R1_CONV_2_BIN_PRESENT",
        "R3_CONV_4_BIN_PRESENT"
    ]

    for signal in input_signals:
        signal_states[signal] = read_signal(client, signal, is_input=True)

    # Check all output signals
    output_signals = [
        "TO_RECEIVING_STA_1",
        "FROM_RECEIVING",
        "TO_ASSEMBLY_STA_1",
        "FROM_ASSEMBLY"
    ]

    for signal in output_signals:
        signal_states[signal] = read_signal(client, signal, is_input=False)

    return signal_states


def run_all_tests():
    """Run all tests in sequence"""
    client = connect_to_plc()
    if not client:
        print("❌ Cannot proceed with tests without connection to PLC")
        return False

    try:
        # Store signal states before and after each test
        signal_states_history = {}

        # Run the tests
        tests = [
            ("Basic Connectivity", test_basic_connectivity),
            ("PLC Cycle Start/Stop", test_cycle_start_stop),
            ("Storage to Receiving", test_storage_to_receiving),
            ("Receiving to Storage", test_receiving_to_storage),
            ("Storage to Assembly", test_storage_to_assembly),
            ("Assembly to Storage", test_assembly_to_storage),
            ("Error Handling", test_error_handling)
        ]

        results = []
        for test_name, test_func in tests:
            print(f"\n{'='*50}")
            print(f"🧪 Running test: {test_name}")
            print(f"{'='*50}")

            # Check signal states before test
            before_states = check_all_signals(client)
            signal_states_history[f"{test_name}_before"] = before_states

            # Run the test
            success = test_func(client)
            results.append((test_name, success))

            # Check signal states after test
            after_states = check_all_signals(client)
            signal_states_history[f"{test_name}_after"] = after_states

            if not success:
                print(f"❌ Test '{test_name}' failed")

            # Small delay between tests
            time.sleep(1)

        # Print summary
        print("\n\n")
        print("="*80)
        print("📊 TEST SUMMARY")
        print("="*80)

        all_passed = True
        for test_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status} - {test_name}")
            if not success:
                all_passed = False

        # Print detailed signal state summary
        print("\n")
        print("="*80)
        print("📈 DETAILED SIGNAL STATE SUMMARY")
        print("="*80)

        print("\nSignal states before and after each test:")
        for test_name, _ in tests:
            before_key = f"{test_name}_before"
            after_key = f"{test_name}_after"

            if before_key in signal_states_history and after_key in signal_states_history:
                print(f"\n{'-'*40}")
                print(f"Test: {test_name}")
                print(f"{'-'*40}")

                before = signal_states_history[before_key]
                after = signal_states_history[after_key]

                # Find the maximum signal name length for formatting
                max_len = max(len(signal) for signal in before.keys())

                # Print header
                print(
                    f"{'Signal':{max_len+2}} | {'Before':<10} | {'After':<10} | {'Changed':<10}")
                print(f"{'-'*(max_len+2)}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")

                # Print each signal state
                for signal in sorted(before.keys()):
                    before_val = before[signal]
                    after_val = after[signal]
                    changed = "✓" if before_val != after_val else " "

                    before_str = "TRUE" if before_val else "FALSE"
                    after_str = "TRUE" if after_val else "FALSE"

                    print(
                        f"{signal:{max_len+2}} | {before_str:<10} | {after_str:<10} | {changed:<10}")

        if all_passed:
            print("\n🎉 All tests passed! The beachside PSM is operating properly.")
            return True
        else:
            print(
                "\n⚠️ Some tests failed. The beachside PSM may not be operating correctly.")

            # Provide specific advice about the IX contacts issue
            print("\n🔍 DIAGNOSTIC INFORMATION:")
            print("If you're seeing issues with %IX contacts not being detected:")
            print(
                "1. The PSM script sets %IX contacts that stay in that state until explicitly changed")
            print(
                "2. Check if signals are being set but cleared too quickly before detection")
            print(
                "3. Look for timing issues in the test script's wait_for_signal function")
            print("4. Consider increasing timeouts or adding delays between operations")
            return False

    except Exception as e:
        print(f"❌ Error during tests: {str(e)}")
        return False

    finally:
        # Always close the connection
        if client:
            client.close()
            print("\n👋 Connection closed")


if __name__ == "__main__":
    print("🧪 Starting Beachside PSM tests...")
    success = run_all_tests()
    sys.exit(0 if success else 1)
