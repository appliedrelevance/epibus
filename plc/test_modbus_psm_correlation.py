#!/usr/bin/env python3
"""
Test script to verify the correlation between Modbus TCP and PSM module.
This script will write values via Modbus TCP and then read them via PSM
to see if they're accessing the same memory space.
"""

from pymodbus.client import ModbusTcpClient
import psm  # type: ignore
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

# Test configuration
HOST = 'openplc'  # OpenPLC simulator hostname
PORT = 502        # Default Modbus TCP port
TIMEOUT = 10      # Default timeout for operations (seconds)

# Address mapping between Modbus TCP and PSM
ADDRESS_MAPPING = [
    # (Modbus address, PSM address, description, is_coil)
    (0, "MW0", "Command Register", False),  # MW0 - Command register
    (11, "QX1.3", "Bin 1", True),           # QX1.3 - PICK_BIN_01
    (12, "QX1.4", "Bin 2", True),           # QX1.4 - PICK_BIN_02
    (32, "QX4.0", "TO_RECEIVING_STA_1", True),  # QX4.0 - TO_RECEIVING_STA_1
    (33, "QX4.1", "FROM_RECEIVING", True),      # QX4.1 - FROM_RECEIVING
    (34, "QX4.2", "TO_ASSEMBLY_STA_1", True),   # QX4.2 - TO_ASSEMBLY_STA_1
    (35, "QX4.3", "FROM_ASSEMBLY", True),       # QX4.3 - FROM_ASSEMBLY
]


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


def initialize_psm():
    """Initialize the PSM module"""
    log.info("🔧 Initializing PSM module...")
    psm.start()
    log.info("✅ PSM module initialized")


def write_modbus_read_psm(client, modbus_address, psm_address, description, is_coil, value):
    """Write a value via Modbus TCP and read it via PSM"""
    try:
        # Write the value via Modbus TCP
        if is_coil:
            result = client.write_coil(address=modbus_address, value=value)
        else:
            result = client.write_register(address=modbus_address, value=value)

        if not result:
            log.error(
                f"❌ Failed to write {value} to {description} via Modbus TCP")
            return False

        log.info(
            f"📝 Wrote {value} to {description} via Modbus TCP (address {modbus_address})")

        # Small delay to ensure the value is propagated
        time.sleep(0.5)

        # Read the value via PSM
        psm_value = psm.get_var(psm_address)
        log.info(
            f"📝 Read {psm_value} from {description} via PSM (address {psm_address})")

        # Compare the values
        if (is_coil and bool(psm_value) == bool(value)) or (not is_coil and psm_value == value):
            log.info(
                f"✅ Values match for {description}: Modbus={value}, PSM={psm_value}")
            return True
        else:
            log.error(
                f"❌ Values do not match for {description}: Modbus={value}, PSM={psm_value}")
            return False
    except Exception as e:
        log.error(f"❌ Error during test for {description}: {str(e)}")
        return False


def write_psm_read_modbus(client, modbus_address, psm_address, description, is_coil, value):
    """Write a value via PSM and read it via Modbus TCP"""
    try:
        # Write the value via PSM
        psm.set_var(psm_address, value)
        log.info(
            f"📝 Wrote {value} to {description} via PSM (address {psm_address})")

        # Small delay to ensure the value is propagated
        time.sleep(0.5)

        # Read the value via Modbus TCP
        if is_coil:
            result = client.read_coils(address=modbus_address, count=1)
            if not hasattr(result, 'bits'):
                log.error(f"❌ Failed to read {description} via Modbus TCP")
                return False
            modbus_value = result.bits[0]
        else:
            result = client.read_holding_registers(
                address=modbus_address, count=1)
            if not hasattr(result, 'registers'):
                log.error(f"❌ Failed to read {description} via Modbus TCP")
                return False
            modbus_value = result.registers[0]

        log.info(
            f"📝 Read {modbus_value} from {description} via Modbus TCP (address {modbus_address})")

        # Compare the values
        if (is_coil and bool(modbus_value) == bool(value)) or (not is_coil and modbus_value == value):
            log.info(
                f"✅ Values match for {description}: PSM={value}, Modbus={modbus_value}")
            return True
        else:
            log.error(
                f"❌ Values do not match for {description}: PSM={value}, Modbus={modbus_value}")
            return False
    except Exception as e:
        log.error(f"❌ Error during test for {description}: {str(e)}")
        return False


def test_modbus_psm_correlation():
    """Test the correlation between Modbus TCP and PSM module"""
    client = connect_to_plc()
    if not client:
        log.error("❌ Cannot proceed with tests without connection to PLC")
        return False

    try:
        initialize_psm()

        log.info("\n🧪 Testing Modbus TCP write -> PSM read...")
        for modbus_address, psm_address, description, is_coil in ADDRESS_MAPPING:
            if is_coil:
                # Test with True
                write_modbus_read_psm(
                    client, modbus_address, psm_address, description, is_coil, True)
                time.sleep(1)
                # Test with False
                write_modbus_read_psm(
                    client, modbus_address, psm_address, description, is_coil, False)
            else:
                # Test with value 1
                write_modbus_read_psm(
                    client, modbus_address, psm_address, description, is_coil, 1)
                time.sleep(1)
                # Test with value 0
                write_modbus_read_psm(
                    client, modbus_address, psm_address, description, is_coil, 0)
            time.sleep(1)

        log.info("\n🧪 Testing PSM write -> Modbus TCP read...")
        for modbus_address, psm_address, description, is_coil in ADDRESS_MAPPING:
            if is_coil:
                # Test with True
                write_psm_read_modbus(
                    client, modbus_address, psm_address, description, is_coil, True)
                time.sleep(1)
                # Test with False
                write_psm_read_modbus(
                    client, modbus_address, psm_address, description, is_coil, False)
            else:
                # Test with value 1
                write_psm_read_modbus(
                    client, modbus_address, psm_address, description, is_coil, 1)
                time.sleep(1)
                # Test with value 0
                write_psm_read_modbus(
                    client, modbus_address, psm_address, description, is_coil, 0)
            time.sleep(1)

        log.info("\n✅ Correlation tests completed")
        return True

    except Exception as e:
        log.error(f"❌ Error during tests: {str(e)}")
        return False

    finally:
        # Always close the connections
        if client:
            client.close()
            log.info("👋 Modbus TCP connection closed")

        log.info("👋 Stopping PSM module")
        psm.stop()


if __name__ == "__main__":
    log.info("🧪 Starting Modbus-PSM correlation tests...")
    test_modbus_psm_correlation()
