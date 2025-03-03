#!/usr/bin/env python3
"""
Script to verify the address mapping between OpenPLC addresses and Modbus addresses.
This script helps ensure that the address conversion is correct.
"""

import logging

# Configure logging
logging.basicConfig(format='%(levelname)s: %(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)

# OpenPLC addressing scheme:
# %IX0.0 - %IX0.7: Discrete inputs 0-7
# %IX1.0 - %IX1.7: Discrete inputs 8-15
# ...
# %QX0.0 - %QX0.7: Coils 0-7
# %QX1.0 - %QX1.7: Coils 8-15
# ...
# %MW0, %MW1, ...: Holding registers 0, 1, ...

# Modbus addressing:
# Discrete inputs: 0-based addressing (0, 1, 2, ...)
# Coils: 0-based addressing (0, 1, 2, ...)
# Holding registers: 0-based addressing (0, 1, 2, ...)


def openplc_to_modbus(openplc_address):
    """
    Convert an OpenPLC address to a Modbus address.

    Args:
        openplc_address (str): OpenPLC address (e.g., "IX0.1", "QX1.3", "MW0")

    Returns:
        tuple: (modbus_address, data_type)
            modbus_address (int): Modbus address
            data_type (str): "discrete_input", "coil", or "holding_register"
    """
    if not openplc_address:
        raise ValueError("OpenPLC address cannot be empty")

    # Handle holding registers (MW)
    if openplc_address.startswith("MW"):
        try:
            register_num = int(openplc_address[2:])
            return register_num, "holding_register"
        except ValueError:
            raise ValueError(
                f"Invalid holding register address: {openplc_address}")

    # Handle discrete inputs (IX) and coils (QX)
    if not (openplc_address.startswith("IX") or openplc_address.startswith("QX")):
        raise ValueError(f"Unsupported address type: {openplc_address}")

    try:
        # Extract the byte and bit parts (e.g., from "IX0.1", byte=0, bit=1)
        parts = openplc_address[2:].split(".")
        if len(parts) != 2:
            raise ValueError(f"Invalid address format: {openplc_address}")

        byte = int(parts[0])
        bit = int(parts[1])

        if bit < 0 or bit > 7:
            raise ValueError(
                f"Bit value must be between 0 and 7: {openplc_address}")

        # Calculate the Modbus address
        modbus_address = byte * 8 + bit

        # Determine the data type
        data_type = "discrete_input" if openplc_address.startswith(
            "IX") else "coil"

        return modbus_address, data_type

    except ValueError as e:
        raise ValueError(
            f"Invalid address format: {openplc_address} - {str(e)}")


def modbus_to_openplc(modbus_address, data_type):
    """
    Convert a Modbus address to an OpenPLC address.

    Args:
        modbus_address (int): Modbus address
        data_type (str): "discrete_input", "coil", or "holding_register"

    Returns:
        str: OpenPLC address (e.g., "IX0.1", "QX1.3", "MW0")
    """
    if modbus_address < 0:
        raise ValueError("Modbus address cannot be negative")

    if data_type == "holding_register":
        return f"MW{modbus_address}"

    if data_type not in ["discrete_input", "coil"]:
        raise ValueError(f"Unsupported data type: {data_type}")

    # Calculate the byte and bit parts
    byte = modbus_address // 8
    bit = modbus_address % 8

    # Determine the prefix
    prefix = "IX" if data_type == "discrete_input" else "QX"

    return f"{prefix}{byte}.{bit}"


def verify_mapping():
    """Verify the mapping between OpenPLC addresses and Modbus addresses"""
    # Test cases from beachside_psm.py and test_beachside_psm_diagnostic.py
    test_cases = [
        # OpenPLC address, Expected Modbus address, Expected data type
        ("MW0", 0, "holding_register"),  # Command register

        # Bin addresses
        ("QX1.3", 11, "coil"),  # PICK_BIN_01
        ("QX1.4", 12, "coil"),  # PICK_BIN_02
        ("QX1.5", 13, "coil"),  # PICK_BIN_03
        ("QX1.6", 14, "coil"),  # PICK_BIN_04
        ("QX1.7", 15, "coil"),  # PICK_BIN_05
        ("QX2.0", 16, "coil"),  # PICK_BIN_06
        ("QX2.1", 17, "coil"),  # PICK_BIN_07
        ("QX2.2", 18, "coil"),  # PICK_BIN_08
        ("QX2.3", 19, "coil"),  # PICK_BIN_09
        ("QX2.4", 20, "coil"),  # PICK_BIN_10
        ("QX2.5", 21, "coil"),  # PICK_BIN_11
        ("QX2.6", 22, "coil"),  # PICK_BIN_12

        # Input signals
        ("IX0.1", 1, "discrete_input"),  # PLC_CYCLE_RUNNING
        ("IX0.2", 2, "discrete_input"),  # PICK_ERROR
        ("IX0.3", 3, "discrete_input"),  # PICK_TO_ASSEMBLY_IN_PROCESS
        ("IX0.4", 4, "discrete_input"),  # PICK_TO_ASSEMBLY_COMPLETE
        ("IX0.5", 5, "discrete_input"),  # PICK_TO_RECEIVING_IN_PROCESS
        ("IX0.6", 6, "discrete_input"),  # PICK_TO_RECEIVING_COMPLETE
        ("IX0.7", 7, "discrete_input"),  # PICK_TO_STORAGE_IN_PROCESS
        ("IX1.0", 8, "discrete_input"),  # PICK_TO_STORAGE_COMPLETE
        ("IX1.1", 9, "discrete_input"),  # R1_CONV_2_BIN_PRESENT
        ("IX1.2", 10, "discrete_input"),  # R3_CONV_4_BIN_PRESENT

        # Output signals
        ("QX4.0", 32, "coil"),  # TO_RECEIVING_STA_1
        ("QX4.1", 33, "coil"),  # FROM_RECEIVING
        ("QX4.2", 34, "coil"),  # TO_ASSEMBLY_STA_1
        ("QX4.3", 35, "coil"),  # FROM_ASSEMBLY
    ]

    log.info("🧪 Verifying OpenPLC to Modbus address mapping...")

    all_passed = True

    for openplc_addr, expected_modbus_addr, expected_data_type in test_cases:
        try:
            modbus_addr, data_type = openplc_to_modbus(openplc_addr)

            if modbus_addr == expected_modbus_addr and data_type == expected_data_type:
                log.info(f"✅ {openplc_addr} -> {modbus_addr} ({data_type})")
            else:
                log.error(
                    f"❌ {openplc_addr} -> {modbus_addr} ({data_type}), expected {expected_modbus_addr} ({expected_data_type})")
                all_passed = False

        except Exception as e:
            log.error(f"❌ Error converting {openplc_addr}: {str(e)}")
            all_passed = False

    log.info("\n🧪 Verifying Modbus to OpenPLC address mapping...")

    for expected_openplc_addr, modbus_addr, data_type in test_cases:
        try:
            openplc_addr = modbus_to_openplc(modbus_addr, data_type)

            if openplc_addr == expected_openplc_addr:
                log.info(f"✅ {modbus_addr} ({data_type}) -> {openplc_addr}")
            else:
                log.error(
                    f"❌ {modbus_addr} ({data_type}) -> {openplc_addr}, expected {expected_openplc_addr}")
                all_passed = False

        except Exception as e:
            log.error(
                f"❌ Error converting {modbus_addr} ({data_type}): {str(e)}")
            all_passed = False

    if all_passed:
        log.info("\n✅ All address mappings verified successfully!")
    else:
        log.error("\n❌ Some address mappings failed verification!")

    return all_passed


if __name__ == "__main__":
    log.info("🧪 Starting address mapping verification...")
    verify_mapping()
