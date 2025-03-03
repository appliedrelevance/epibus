#!/usr/bin/env python3
"""
Test script to verify the mapping between Modbus TCP addresses and PSM module addresses.
This script will write values to specific addresses and verify they're being set correctly.
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
}

# MODBUS Signal Addresses (converted from beachside_psm.py to OpenPLC Modbus addresses)
SIGNALS = {
    # Output signals (QX) - From ERP to PLC
    "TO_RECEIVING_STA_1": 32,     # QX4.0 (4*8+0 = 32)
    "FROM_RECEIVING": 33,         # QX4.1 (4*8+1 = 33)
    "TO_ASSEMBLY_STA_1": 34,      # QX4.2 (4*8+2 = 34)
    "FROM_ASSEMBLY": 35           # QX4.3 (4*8+3 = 35)
}

# Command register
COMMAND_REGISTER = 0  # MW0 - Memory Word 0 (first holding register)

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


def test_address_mapping():
    """Test the mapping between Modbus TCP addresses and PSM module addresses"""
    client = connect_to_plc()
    if not client:
        log.error("❌ Cannot proceed with tests without connection to PLC")
        return False

    try:
        log.info("\n🧪 Testing command register (MW0)...")
        # Test command register (MW0)
        write_and_verify_register(
            client, COMMAND_REGISTER, 1, "Command Register (MW0)")
        time.sleep(2)  # Give the PLC time to process the command
        write_and_verify_register(
            client, COMMAND_REGISTER, 0, "Command Register (MW0)")
        time.sleep(2)  # Give the PLC time to process the command

        log.info("\n🧪 Testing bin selection addresses...")
        # Test bin selection addresses
        for bin_num, address in BIN_ADDRESSES.items():
            write_and_verify_coil(client, address, True, f"Bin {bin_num}")
            time.sleep(2)  # Give the PLC time to process the command
            write_and_verify_coil(client, address, False, f"Bin {bin_num}")
            time.sleep(2)  # Give the PLC time to process the command

        log.info("\n🧪 Testing station selection addresses...")
        # Test station selection addresses
        for name, address in SIGNALS.items():
            write_and_verify_coil(client, address, True, name)
            time.sleep(2)  # Give the PLC time to process the command
            write_and_verify_coil(client, address, False, name)
            time.sleep(2)  # Give the PLC time to process the command

        log.info("\n🧪 Testing combined bin and station selection...")
        # Test combined bin and station selection
        bin_address = BIN_ADDRESSES[1]
        station_address = SIGNALS["TO_RECEIVING_STA_1"]

        # Set bin 1
        write_and_verify_coil(client, bin_address, True, "Bin 1")
        time.sleep(1)

        # Set TO_RECEIVING_STA_1
        write_and_verify_coil(client, station_address,
                              True, "TO_RECEIVING_STA_1")
        time.sleep(5)  # Give the PLC time to process the combined signals

        # Clear both signals
        write_and_verify_coil(client, bin_address, False, "Bin 1")
        write_and_verify_coil(client, station_address,
                              False, "TO_RECEIVING_STA_1")

        log.info("\n✅ Address mapping tests completed")
        return True

    except Exception as e:
        log.error(f"❌ Error during tests: {str(e)}")
        return False

    finally:
        # Always close the connection
        if client:
            client.close()
            log.info("\n👋 Connection closed")


if __name__ == "__main__":
    log.info("🧪 Starting Modbus-PSM mapping tests...")
    test_address_mapping()
