# -*- coding: utf-8 -*-
# Script to check Modbus signal values directly in the database
# Run with: bench execute epibus.epibus.check_modbus_db_values.check_device_db_values --args "US15-B10-B1"

import frappe
import json
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger("modbus_db_check")


def check_device_db_values(device_name):
    """
    Check the database values for Modbus signals of a specific device

    Args:
        device_name: Name of the Modbus Connection document
    """
    frappe.init(site="site1.local")
    frappe.connect()

    logger.info(f"Checking database values for device: {device_name}")

    try:
        # Get the device document
        device_doc = frappe.get_doc("Modbus Connection", device_name)
        if not device_doc:
            logger.error(f"Device {device_name} not found")
            return

        logger.info(
            f"Device found: {device_doc.get('device_name')} ({device_doc.get('host')}:{device_doc.get('port')})")

        # Get all signals for this device
        signals = frappe.get_all(
            "Modbus Signal",
            filters={"parent": device_name},
            fields=["name", "signal_name", "signal_type", "modbus_address"]
        )

        logger.info(f"Found {len(signals)} signals for device {device_name}")

        # Check each signal's database values
        for signal_info in signals:
            try:
                # Get the full signal document
                signal_doc = frappe.get_doc("Modbus Signal", signal_info.name)

                logger.info(
                    f"Signal: {signal_doc.signal_name}, Type: {signal_doc.signal_type}, Address: {signal_doc.modbus_address}")

                # Check for digital_value field
                if hasattr(signal_doc, "digital_value"):
                    logger.info(
                        f"  digital_value in DB: {signal_doc.digital_value}")
                else:
                    logger.info("  digital_value field not found in document")

                # Check for float_value field
                if hasattr(signal_doc, "float_value"):
                    logger.info(
                        f"  float_value in DB: {signal_doc.float_value}")
                else:
                    logger.info("  float_value field not found in document")

                # Check raw database values using frappe.db
                db_values = frappe.db.get_value(
                    "Modbus Signal",
                    signal_doc.name,
                    ["digital_value", "float_value", "modified"],
                    as_dict=True
                )

                if db_values:
                    logger.info(
                        f"  DB digital_value: {db_values.get('digital_value')}")
                    logger.info(
                        f"  DB float_value: {db_values.get('float_value')}")
                    logger.info(
                        f"  Last modified: {db_values.get('modified')}")
                else:
                    logger.info("  No database values found")

                # Check if the fields exist in the DocType definition
                doctype_fields = frappe.get_meta(
                    "Modbus Signal").get_fieldnames_with_value()
                logger.info(
                    f"  Fields in DocType: {'digital_value' in doctype_fields}, {'float_value' in doctype_fields}")

            except Exception as e:
                logger.error(
                    f"Error checking signal {signal_info.name}: {str(e)}")

        # Check if there are any issues with the DocType definition
        try:
            doctype = frappe.get_doc("DocType", "Modbus Signal")
            fields = [f.fieldname for f in doctype.fields]
            logger.info(f"Fields defined in Modbus Signal DocType: {fields}")

            # Check if the required fields are present
            required_fields = ["digital_value", "float_value"]
            missing_fields = [f for f in required_fields if f not in fields]

            if missing_fields:
                logger.error(
                    f"Missing fields in DocType definition: {missing_fields}")

                # Check if we need to add the fields
                logger.info(
                    "Checking if fields need to be added to DocType...")

                for field_name in missing_fields:
                    # Check if the field exists in the database table
                    try:
                        # Try to query the field directly from the database
                        query = f"SELECT `{field_name}` FROM `tabModbus Signal` WHERE name=%s LIMIT 1"
                        result = frappe.db.sql(
                            query, (signals[0].name if signals else None))

                        if result is not None:
                            logger.info(
                                f"Field {field_name} exists in database table but not in DocType definition")
                        else:
                            logger.info(
                                f"Field {field_name} does not exist in database table")
                    except Exception as e:
                        logger.error(
                            f"Error checking field {field_name} in database: {str(e)}")

        except Exception as e:
            logger.error(f"Error checking DocType definition: {str(e)}")

        # Check the warehouse_dashboard.get_modbus_data function
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
                    f"Connection found in get_modbus_data: {target_connection.get('device_name')}")
                logger.info(
                    f"Number of signals: {len(target_connection.get('signals', []))}")

                for signal in target_connection.get('signals', []):
                    logger.info(
                        f"Signal: {signal.get('signal_name')}, Value from API: {signal.get('value')}")
            else:
                logger.error(
                    f"Connection {device_name} not found in get_modbus_data results")

        except Exception as e:
            logger.error(f"Error checking get_modbus_data: {str(e)}")

    except Exception as e:
        logger.error(f"Error in check_device_db_values: {str(e)}")

    logger.info("Database check complete")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        check_device_db_values(sys.argv[1])
    else:
        print("Please provide a device name")
