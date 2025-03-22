# -*- coding: utf-8 -*-
# Debug script for Modbus connection issues
# Run with: bench execute epibus.epibus.debug_modbus_connection.debug_device --args "US15-B10-B1"

import frappe
import traceback
from pymodbus.client import ModbusTcpClient
from pymodbus.framer import FramerType
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.utils.signal_handler import SignalHandler
from epibus.epibus.doctype.modbus_connection.modbus_connection import ModbusConnection

logger = get_logger("modbus_debug")


def debug_device(device_name):
    """
    Debug a specific Modbus device connection and signal values

    Args:
        device_name: Name of the Modbus Connection document
    """
    frappe.init(site="site1.local")
    frappe.connect()

    logger.info(f"Starting debug for device: {device_name}")

    try:
        # Get the device document
        device_doc = frappe.get_doc("Modbus Connection", device_name)
        if not device_doc:
            logger.error(f"Device {device_name} not found")
            return

        logger.info(
            f"Device found: {device_doc.device_name} ({device_doc.host}:{device_doc.port})")
        logger.info(f"Device enabled: {device_doc.enabled}")

        # Test direct connection
        logger.info("Testing direct connection...")
        try:
            client = ModbusTcpClient(
                host=device_doc.host,
                port=device_doc.port,
                framer=FramerType.SOCKET,
                timeout=10,
                retries=5,
                reconnect_delay=1
            )

            if client.connect():
                logger.info("Direct connection successful")

                # Test basic Modbus functions
                try:
                    logger.info("Testing basic Modbus functions...")

                    # Try reading coils (function code 1)
                    coil_response = client.read_coils(0, 1)
                    if hasattr(coil_response, 'bits'):
                        logger.info(f"Read coil 0: {coil_response.bits[0]}")
                    else:
                        logger.error(f"Coil read error: {coil_response}")

                    # Try reading discrete inputs (function code 2)
                    input_response = client.read_discrete_inputs(0, 1)
                    if hasattr(input_response, 'bits'):
                        logger.info(
                            f"Read discrete input 0: {input_response.bits[0]}")
                    else:
                        logger.error(
                            f"Discrete input read error: {input_response}")

                    # Try reading holding registers (function code 3)
                    holding_response = client.read_holding_registers(0, 1)
                    if hasattr(holding_response, 'registers'):
                        logger.info(
                            f"Read holding register 0: {holding_response.registers[0]}")
                    else:
                        logger.error(
                            f"Holding register read error: {holding_response}")

                    # Try reading input registers (function code 4)
                    input_reg_response = client.read_input_registers(0, 1)
                    if hasattr(input_reg_response, 'registers'):
                        logger.info(
                            f"Read input register 0: {input_reg_response.registers[0]}")
                    else:
                        logger.error(
                            f"Input register read error: {input_reg_response}")

                except Exception as e:
                    logger.error(
                        f"Error testing basic Modbus functions: {str(e)}")
                    logger.error(traceback.format_exc())

                client.close()
            else:
                logger.error("Direct connection failed")
        except Exception as e:
            logger.error(f"Error establishing direct connection: {str(e)}")
            logger.error(traceback.format_exc())

        # Test connection through device_doc.get_client()
        logger.info("Testing connection through device_doc.get_client()...")
        try:
            client = device_doc.get_client()
            logger.info(
                "Connection through device_doc.get_client() successful")

            # Test reading signals
            logger.info(f"Testing {len(device_doc.signals)} signals...")

            for signal in device_doc.signals:
                try:
                    logger.info(
                        f"Signal: {signal.signal_name}, Type: {signal.signal_type}, Address: {signal.modbus_address}")

                    # Check if signal has the expected fields
                    logger.info(
                        f"Signal has digital_value field: {hasattr(signal, 'digital_value')}")
                    logger.info(
                        f"Signal has float_value field: {hasattr(signal, 'float_value')}")

                    # Try reading the signal directly
                    handler = SignalHandler(client)
                    try:
                        value = handler.read(
                            signal.signal_type, signal.modbus_address)
                        logger.info(f"Direct read value: {value}")
                    except Exception as e:
                        logger.error(f"Error in direct read: {str(e)}")

                    # Try reading through the signal's read_signal method
                    try:
                        value = signal.read_signal()
                        logger.info(f"read_signal() value: {value}")
                    except Exception as e:
                        logger.error(f"Error in read_signal(): {str(e)}")
                        logger.error(traceback.format_exc())

                except Exception as e:
                    logger.error(
                        f"Error processing signal {signal.signal_name}: {str(e)}")
                    logger.error(traceback.format_exc())

        except Exception as e:
            logger.error(f"Error with device_doc.get_client(): {str(e)}")
            logger.error(traceback.format_exc())

        # Test the warehouse_dashboard.get_modbus_data function
        logger.info("Testing warehouse_dashboard.get_modbus_data function...")
        try:
            from epibus.www.warehouse_dashboard import get_modbus_data

            connections = get_modbus_data()
            target_connection = None

            for conn in connections:
                if conn.get('name') == device_name:
                    target_connection = conn
                    break

            if target_connection:
                logger.info(
                    f"Found connection in get_modbus_data: {target_connection.get('device_name')}")
                logger.info(
                    f"Number of signals: {len(target_connection.get('signals', []))}")

                for signal in target_connection.get('signals', []):
                    logger.info(
                        f"Signal: {signal.get('signal_name')}, Value: {signal.get('value')}")
            else:
                logger.error(
                    f"Connection {device_name} not found in get_modbus_data results")

        except Exception as e:
            logger.error(f"Error testing get_modbus_data: {str(e)}")
            logger.error(traceback.format_exc())

    except Exception as e:
        logger.error(f"Error in debug_device: {str(e)}")
        logger.error(traceback.format_exc())

    logger.info("Debug complete")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        debug_device(sys.argv[1])
    else:
        print("Please provide a device name")
