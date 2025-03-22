# -*- coding: utf-8 -*-
# Fix script for Modbus signals returning null values
# Run with: bench execute epibus.epibus.fix_modbus_signals.fix_device_signals --args "US15-B10-B1"

import frappe
import traceback
from pymodbus.client import ModbusTcpClient
from pymodbus.framer import FramerType
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.utils.signal_handler import SignalHandler
from epibus.epibus.doctype.modbus_connection.modbus_connection import ModbusConnection
from epibus.epibus.utils.signal_monitor import publish_signal_update

logger = get_logger("modbus_fix")


def fix_device_signals(device_name):
    """
    Fix signals for a specific Modbus device that are returning null values

    Args:
        device_name: Name of the Modbus Connection document
    """
    frappe.init(site="site1.local")
    frappe.connect()

    logger.info(f"Starting fix for device: {device_name}")

    try:
        # Get the device document
        device_doc = frappe.get_doc("Modbus Connection", device_name)
        if not device_doc:
            logger.error(f"Device {device_name} not found")
            return

        logger.info(
            f"Device found: {device_doc.device_name} ({device_doc.host}:{device_doc.port})")

        # Ensure device is enabled
        if not device_doc.enabled:
            logger.info("Device is disabled, enabling it...")
            device_doc.enabled = 1
            device_doc.save()
            logger.info("Device enabled successfully")

        # Test connection
        try:
            client = device_doc.get_client()
            logger.info("Connection successful")

            # Process each signal
            fixed_count = 0
            error_count = 0

            for signal in device_doc.signals:
                try:
                    logger.info(
                        f"Processing signal: {signal.signal_name}, Type: {signal.signal_type}, Address: {signal.modbus_address}")

                    # Try reading the signal directly using SignalHandler
                    handler = SignalHandler(client)
                    try:
                        value = handler.read(
                            signal.signal_type, signal.modbus_address)
                        logger.info(f"Read value: {value}")

                        # Update the signal value in the database
                        if value is not None:
                            if isinstance(value, bool):
                                # For digital signals
                                signal.db_set('digital_value',
                                              value, update_modified=False)
                                logger.info(
                                    f"Updated digital_value to {value}")
                            elif isinstance(value, (int, float)):
                                # For analog signals
                                signal.db_set('float_value', float(
                                    value), update_modified=False)
                                logger.info(f"Updated float_value to {value}")

                            # Publish the update to the realtime system
                            publish_signal_update(signal.name, value)
                            logger.info(f"Published update for {signal.name}")

                            fixed_count += 1
                        else:
                            logger.error(
                                f"Read value is None for signal {signal.signal_name}")
                            error_count += 1

                    except Exception as e:
                        logger.error(
                            f"Error reading signal {signal.signal_name}: {str(e)}")
                        logger.error(traceback.format_exc())
                        error_count += 1

                        # Try with different address format or offset as a fallback
                        try:
                            logger.info(
                                f"Trying alternative address for {signal.signal_name}...")

                            # Try with address offset by 1 (some PLCs use 0-based vs 1-based addressing)
                            alt_address = signal.modbus_address + 1
                            value = handler.read(
                                signal.signal_type, alt_address)
                            logger.info(
                                f"Read value with alternative address {alt_address}: {value}")

                            if value is not None:
                                # Update the signal with the new address and value
                                signal.modbus_address = alt_address

                                if isinstance(value, bool):
                                    signal.db_set(
                                        'digital_value', value, update_modified=False)
                                elif isinstance(value, (int, float)):
                                    signal.db_set('float_value', float(
                                        value), update_modified=False)

                                signal.save()
                                publish_signal_update(signal.name, value)
                                logger.info(
                                    f"Fixed signal {signal.signal_name} with alternative address")
                                fixed_count += 1
                                error_count -= 1  # Subtract the previous error

                        except Exception as alt_e:
                            logger.error(
                                f"Alternative address also failed: {str(alt_e)}")

                except Exception as e:
                    logger.error(
                        f"Error processing signal {signal.signal_name}: {str(e)}")
                    logger.error(traceback.format_exc())
                    error_count += 1

            logger.info(
                f"Fix complete. Fixed {fixed_count} signals. Errors: {error_count}")

            # Verify fix by checking the warehouse_dashboard.get_modbus_data function
            try:
                from epibus.www.warehouse_dashboard import get_modbus_data

                connections = get_modbus_data()
                target_connection = None

                for conn in connections:
                    if conn.get('name') == device_name:
                        target_connection = conn
                        break

                if target_connection:
                    null_count = 0
                    valid_count = 0

                    for signal in target_connection.get('signals', []):
                        if signal.get('value') is None:
                            null_count += 1
                        else:
                            valid_count += 1

                    logger.info(
                        f"Verification: {valid_count} signals have values, {null_count} signals are still null")

                    if null_count > 0:
                        logger.warning(
                            f"Some signals ({null_count}) still have null values")
                    else:
                        logger.info("All signals now have valid values")

            except Exception as e:
                logger.error(f"Error verifying fix: {str(e)}")
                logger.error(traceback.format_exc())

        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            logger.error(traceback.format_exc())

            # Check if this is a hostname resolution issue
            if "Name or service not known" in str(e) or "getaddrinfo failed" in str(e):
                logger.info(
                    "Possible hostname resolution issue. Checking if 'openplc' is an IP address...")

                # Try with IP address if hostname doesn't resolve
                if device_doc.host == "openplc":
                    logger.info(
                        "Trying with IP address 192.168.1.10 instead of 'openplc'...")

                    # Update the host to use IP address
                    original_host = device_doc.host
                    device_doc.host = "192.168.1.10"  # Common default for PLCs
                    device_doc.save()

                    try:
                        client = device_doc.get_client()
                        logger.info(
                            f"Connection successful with IP address {device_doc.host}")
                        # If we get here, the connection worked with the IP address
                    except Exception as ip_e:
                        logger.error(
                            f"Connection with IP address also failed: {str(ip_e)}")
                        # Revert to original hostname
                        device_doc.host = original_host
                        device_doc.save()
                        logger.info(
                            f"Reverted to original hostname: {original_host}")

    except Exception as e:
        logger.error(f"Error in fix_device_signals: {str(e)}")
        logger.error(traceback.format_exc())

    logger.info("Fix attempt complete")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        fix_device_signals(sys.argv[1])
    else:
        print("Please provide a device name")
