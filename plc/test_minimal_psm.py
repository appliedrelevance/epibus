#!/usr/bin/env python3
"""
Test script for beachside_minimal_psm.py
This script tests the minimal PSM by setting bin 1 and monitoring the signals.
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

# Constants - converted to OpenPLC Modbus addresses
BIN_1_ADDRESS = 11  # QX1.3 - PICK_BIN_01 (8 bits per byte, so 1*8+3 = 11)
PICK_TO_RECEIVING_IN_PROCESS = 5  # IX0.5 (0*8+5 = 5)
PICK_TO_RECEIVING_COMPLETE = 6  # IX0.6 (0*8+6 = 6)

# Test configuration
HOST = 'openplc'  # OpenPLC simulator hostname
PORT = 502        # Default Modbus TCP port
TIMEOUT = 30      # Default timeout for operations (seconds)


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


def read_signal(client, address, is_input=True):
    """Read a signal from the PLC"""
    try:
        if is_input:
            result = client.read_discrete_inputs(address=address, count=1)
        else:
            result = client.read_coils(address=address, count=1)

        if hasattr(result, 'bits'):
            return result.bits[0]
        else:
            log.error(
                f"❌ Failed to read signal at address {address}: {result}")
            return None
    except Exception as e:
        log.error(f"❌ Error reading signal at address {address}: {str(e)}")
        return None


def write_coil(client, address, value):
    """Write a value to a coil on the PLC"""
    try:
        result = client.write_coil(address=address, value=value)
        if result:
            log.info(f"✅ Successfully wrote {value} to address {address}")
            return True
        else:
            log.error(f"❌ Failed to write {value} to address {address}")
            return False
    except Exception as e:
        log.error(f"❌ Error writing to address {address}: {str(e)}")
        return False


def wait_for_signal(client, address, expected_value=True, timeout=TIMEOUT, is_input=True, poll_interval=0.5):
    """Wait for a signal to reach the expected value with timeout"""
    log.info(
        f"⏳ Waiting for address {address} to be {expected_value} (timeout: {timeout}s)...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        value = read_signal(client, address, is_input)

        if value == expected_value:
            log.info(f"✅ Signal at address {address} is now {expected_value}")
            return True

        time.sleep(poll_interval)

    log.error(
        f"⏰ Timeout waiting for address {address} to be {expected_value}")
    return False


def read_all_signals(client):
    """Read all relevant signals and print their values"""
    print("\n📊 Current Signal States:")
    print("=" * 40)

    # Read bin 1 state
    bin1_value = read_signal(client, BIN_1_ADDRESS, is_input=False)
    print(f"Bin 1 (QX1.3): {bin1_value}")

    # Read process signals
    in_process = read_signal(
        client, PICK_TO_RECEIVING_IN_PROCESS, is_input=True)
    complete = read_signal(client, PICK_TO_RECEIVING_COMPLETE, is_input=True)

    print(f"PICK_TO_RECEIVING_IN_PROCESS (IX0.5): {in_process}")
    print(f"PICK_TO_RECEIVING_COMPLETE (IX0.6): {complete}")

    print("=" * 40)


def test_minimal_psm():
    """Test the minimal PSM workflow"""
    client = connect_to_plc()
    if not client:
        log.error("❌ Cannot proceed with test without connection to PLC")
        return False

    try:
        # Read initial state
        log.info("\n🔍 Reading initial state...")
        read_all_signals(client)

        # Reset bin 1 to ensure clean state
        log.info("\n🔄 Resetting bin 1...")
        write_coil(client, BIN_1_ADDRESS, False)
        time.sleep(1)
        read_all_signals(client)

        # Set bin 1 to trigger the workflow
        log.info("\n📝 Setting bin 1...")
        write_coil(client, BIN_1_ADDRESS, True)

        # Wait for PICK_TO_RECEIVING_IN_PROCESS to become true (should happen after 10 seconds)
        log.info("\n⏳ Waiting for PICK_TO_RECEIVING_IN_PROCESS to become true...")
        if not wait_for_signal(client, PICK_TO_RECEIVING_IN_PROCESS, True, TIMEOUT, True):
            log.error(
                "❌ PICK_TO_RECEIVING_IN_PROCESS did not become true within timeout")
            return False

        read_all_signals(client)

        # Wait for PICK_TO_RECEIVING_COMPLETE to become true (should happen after another 10 seconds)
        log.info("\n⏳ Waiting for PICK_TO_RECEIVING_COMPLETE to become true...")
        if not wait_for_signal(client, PICK_TO_RECEIVING_COMPLETE, True, TIMEOUT, True):
            log.error(
                "❌ PICK_TO_RECEIVING_COMPLETE did not become true within timeout")
            return False

        read_all_signals(client)

        # Wait for both signals to be reset
        log.info("\n⏳ Waiting for signals to be reset...")
        if not wait_for_signal(client, PICK_TO_RECEIVING_IN_PROCESS, False, TIMEOUT, True):
            log.error(
                "❌ PICK_TO_RECEIVING_IN_PROCESS was not reset within timeout")
            return False

        if not wait_for_signal(client, PICK_TO_RECEIVING_COMPLETE, False, TIMEOUT, True):
            log.error("❌ PICK_TO_RECEIVING_COMPLETE was not reset within timeout")
            return False

        read_all_signals(client)

        # Reset bin 1 to complete the test
        log.info("\n🔄 Resetting bin 1...")
        write_coil(client, BIN_1_ADDRESS, False)
        time.sleep(1)
        read_all_signals(client)

        log.info("\n✅ Test completed successfully!")
        return True

    except Exception as e:
        log.error(f"❌ Error during test: {str(e)}")
        return False

    finally:
        # Always close the connection
        if client:
            client.close()
            log.info("\n👋 Connection closed")


if __name__ == "__main__":
    log.info("🧪 Starting minimal PSM test...")
    test_minimal_psm()
