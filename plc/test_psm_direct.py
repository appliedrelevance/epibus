#!/usr/bin/env python3
"""
Test script to directly interact with the PSM module.
This script will write values to specific addresses using the PSM module
and verify they're being set correctly.
"""

import psm  # type: ignore
import time
import logging

# Configure logging
logging.basicConfig(format='%(levelname)s: %(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

# Map bin numbers to their addresses (from beachside_psm.py)
BIN_ADDRESSES = {
    1: "QX1.3",  # PICK_BIN_01
    2: "QX1.4",  # PICK_BIN_02
}

# MODBUS Signal Addresses (from beachside_psm.py)
SIGNALS = {
    # Output signals (QX) - From ERP to PLC
    "TO_RECEIVING_STA_1": "QX4.0",
    "FROM_RECEIVING": "QX4.1",
    "TO_ASSEMBLY_STA_1": "QX4.2",
    "FROM_ASSEMBLY": "QX4.3"
}


def initialize_psm():
    """Initialize the PSM module"""
    log.info("🔧 Initializing PSM module...")
    psm.start()
    log.info("✅ PSM module initialized")


def write_and_verify_var(address, value, description):
    """Write a value to a variable and verify it was set correctly"""
    try:
        # Write the value
        psm.set_var(address, value)
        log.info(f"📝 Wrote {value} to {description} ({address})")

        # Read back the value to verify
        read_value = psm.get_var(address)
        if read_value == value:
            log.info(
                f"✅ Verification successful for {description} ({address}): {read_value}")
            return True
        else:
            log.error(
                f"❌ Verification failed for {description} ({address}): wrote {value}, read back {read_value}")
            return False
    except Exception as e:
        log.error(
            f"❌ Error writing/reading {description} ({address}): {str(e)}")
        return False


def test_psm_variables():
    """Test writing and reading variables using the PSM module"""
    log.info("\n🧪 Testing command register (MW0)...")
    # Test command register (MW0)
    write_and_verify_var("MW0", 1, "Command Register")
    time.sleep(2)  # Give time to observe the effect
    write_and_verify_var("MW0", 0, "Command Register")
    time.sleep(2)  # Give time to observe the effect

    log.info("\n🧪 Testing bin selection addresses...")
    # Test bin selection addresses
    for bin_num, address in BIN_ADDRESSES.items():
        write_and_verify_var(address, True, f"Bin {bin_num}")
        time.sleep(2)  # Give time to observe the effect
        write_and_verify_var(address, False, f"Bin {bin_num}")
        time.sleep(2)  # Give time to observe the effect

    log.info("\n🧪 Testing station selection addresses...")
    # Test station selection addresses
    for name, address in SIGNALS.items():
        write_and_verify_var(address, True, name)
        time.sleep(2)  # Give time to observe the effect
        write_and_verify_var(address, False, name)
        time.sleep(2)  # Give time to observe the effect

    log.info("\n🧪 Testing combined bin and station selection...")
    # Test combined bin and station selection
    bin_address = BIN_ADDRESSES[1]
    station_address = SIGNALS["TO_RECEIVING_STA_1"]

    # Set bin 1
    write_and_verify_var(bin_address, True, "Bin 1")
    time.sleep(1)

    # Set TO_RECEIVING_STA_1
    write_and_verify_var(station_address, True, "TO_RECEIVING_STA_1")
    time.sleep(5)  # Give time to observe the effect

    # Clear both signals
    write_and_verify_var(bin_address, False, "Bin 1")
    write_and_verify_var(station_address, False, "TO_RECEIVING_STA_1")

    log.info("\n✅ PSM variable tests completed")


def dump_all_variables():
    """Dump all relevant variables for debugging"""
    log.info("\n🔍 Current Variable Values:")
    log.info("-" * 40)

    # Command register
    command = psm.get_var("MW0")
    log.info(f"Command Register (MW0): {command}")

    # Input signals
    log.info("\nInput Signals (From PLC to ERP):")
    input_signals = {
        "PLC_CYCLE_RUNNING": "IX0.1",
        "PICK_ERROR": "IX0.2",
        "PICK_TO_ASSEMBLY_IN_PROCESS": "IX0.3",
        "PICK_TO_ASSEMBLY_COMPLETE": "IX0.4",
        "PICK_TO_RECEIVING_IN_PROCESS": "IX0.5",
        "PICK_TO_RECEIVING_COMPLETE": "IX0.6",
        "PICK_TO_STORAGE_IN_PROCESS": "IX0.7",
        "PICK_TO_STORAGE_COMPLETE": "IX1.0",
        "R1_CONV_2_BIN_PRESENT": "IX1.1",
        "R3_CONV_4_BIN_PRESENT": "IX1.2",
    }
    for name, address in input_signals.items():
        value = psm.get_var(address)
        log.info(f"  {name} ({address}): {value}")

    # Output signals
    log.info("\nOutput Signals (From ERP to PLC):")
    for name, address in SIGNALS.items():
        value = psm.get_var(address)
        log.info(f"  {name} ({address}): {value}")

    # Bin selections
    log.info("\nBin Selections:")
    for bin_num, address in BIN_ADDRESSES.items():
        value = psm.get_var(address)
        log.info(f"  Bin {bin_num} ({address}): {value}")

    log.info("-" * 40)


if __name__ == "__main__":
    log.info("🧪 Starting direct PSM module tests...")
    try:
        initialize_psm()
        dump_all_variables()  # Dump initial state
        test_psm_variables()
        dump_all_variables()  # Dump final state
    except Exception as e:
        log.error(f"❌ Error during tests: {str(e)}")
    finally:
        log.info("👋 Stopping PSM module")
        psm.stop()
