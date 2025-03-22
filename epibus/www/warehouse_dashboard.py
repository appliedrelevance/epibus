# -*- coding: utf-8 -*-
# Copyright (c) 2023, Applied Relevance and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint
import json
from typing import Dict, List, Any, Optional

no_cache = 1


def get_context(context):
    """
    Prepare the context for the warehouse dashboard page.
    Ensures the page has access to the current user's session.
    """
    # Set up page context
    context.no_cache = 1
    context.no_breadcrumbs = 1
    context.no_header = 1
    context.no_footer = 1

    # Ensure user is logged in
    if frappe.session.user == 'Guest':
        frappe.throw(
            _("Please login to access the Warehouse Dashboard"), frappe.PermissionError)

    # Add user info to context for debugging
    context.user = frappe.session.user

    # Ensure CSRF token is available in the session
    if not frappe.session.csrf_token:
        frappe.session.csrf_token = frappe.generate_hash()

    # Add CSRF token to context
    context.csrf_token = frappe.session.csrf_token

    frappe.logger().info(
        f"Warehouse dashboard accessed by user: {frappe.session.user}")
    frappe.logger().debug(
        f"CSRF token for session: {frappe.session.csrf_token[:5]}...")

    return context


@frappe.whitelist()
def get_modbus_data():
    """
    Get all Modbus connections and their signals.
    Uses the current user's permissions to access the data.

    Returns:
        List[Dict[str, Any]]: A list of Modbus connections with their signals.
    """
    try:
        # Log the current user for debugging
        current_user = frappe.session.user
        frappe.logger().info(f"Fetching Modbus data as user: {current_user}")

        # Get all enabled Modbus connections
        # Remove allow_guest=True to ensure proper permission checking
        connections = frappe.get_all(
            "Modbus Connection",
            fields=["name", "device_name", "device_type",
                    "host", "port", "enabled"],
            filters={"enabled": 1},
            order_by="device_name asc"
        )

        frappe.logger().info(f"Found {len(connections)} Modbus connections")

        # For each connection, get its signals
        for connection in connections:
            # Get signals without the 'value' field which doesn't exist in the table
            signals = frappe.get_all(
                "Modbus Signal",
                fields=["name", "signal_name",
                        "signal_type", "modbus_address"],
                filters={"parent": connection.name},
                order_by="signal_name asc"
            )

            # Get the device document for direct reading if needed
            device_doc = None

            # For each signal, get the actual document to access its current value
            for signal in signals:
                try:
                    # Get the full signal document to access its current value
                    signal_doc = frappe.get_doc("Modbus Signal", signal.name)

                    # The actual value might be stored in different fields based on signal type
                    # Add the current value to the signal object
                    if hasattr(signal_doc, "current_value") and signal_doc.current_value is not None:
                        signal["value"] = signal_doc.current_value
                    elif hasattr(signal_doc, "float_value") and signal_doc.float_value is not None:
                        signal["value"] = signal_doc.float_value
                    elif hasattr(signal_doc, "digital_value") and signal_doc.digital_value is not None:
                        signal["value"] = signal_doc.digital_value
                    else:
                        # Try to read the value directly from the device if database values are null
                        try:
                            # Initialize device_doc only if needed
                            if device_doc is None:
                                device_doc = frappe.get_doc(
                                    "Modbus Connection", connection.name)

                            # Read the signal value directly
                            frappe.logger().info(
                                f"Attempting to read signal {signal.name} directly from device {connection.name}")

                            # Use the read_signal method to get the current value
                            value = signal_doc.read_signal()
                            signal["value"] = value

                            # Update the database with the read value
                            if value is not None:
                                if isinstance(value, bool):
                                    signal_doc.db_set(
                                        'digital_value', value, update_modified=False)
                                elif isinstance(value, (int, float)):
                                    signal_doc.db_set('float_value', float(
                                        value), update_modified=False)

                                frappe.logger().info(
                                    f"Updated database value for signal {signal.name}: {value}")
                            else:
                                signal["value"] = None
                                frappe.logger().warning(
                                    f"Direct read returned None for signal {signal.name}")
                        except Exception as read_error:
                            frappe.logger().error(
                                f"Error reading signal {signal.name} directly: {str(read_error)}")
                            signal["value"] = None

                    frappe.logger().debug(
                        f"Signal {signal.name} value: {signal.get('value')}")
                except Exception as signal_error:
                    frappe.logger().error(
                        f"Error getting value for signal {signal.name}: {str(signal_error)}")
                    signal["value"] = None

            # Add signals to the connection
            connection["signals"] = signals
            frappe.logger().info(
                f"Connection {connection.name} has {len(signals)} signals")

        return connections

    except Exception as e:
        frappe.logger().error(f"Error in get_modbus_data: {str(e)}")
        frappe.log_error(f"Error in get_modbus_data: {str(e)}")
        frappe.throw(_("Error fetching Modbus data: {0}").format(str(e)))
        return []  # This will never be reached due to frappe.throw, but satisfies the type checker


@frappe.whitelist()
def set_signal_value(signal_id: str, value: Any):
    """
    Set the value of a Modbus signal.
    Uses the current user's permissions to update the signal.

    Args:
        signal_id (str): The ID of the signal to update.
        value (Any): The new value for the signal.

    Returns:
        Dict[str, Any]: A dictionary with the status of the operation.
    """
    try:
        # Log the current user for debugging
        current_user = frappe.session.user
        frappe.logger().info(
            f"Setting signal value as user: {current_user} for signal: {signal_id}")

        # Convert value to the appropriate type based on signal type
        signal = frappe.get_doc("Modbus Signal", signal_id)
        signal_type = signal.get("signal_type", "")

        if "Digital" in signal_type:
            # For digital signals, convert to 0 or 1
            value = 1 if cint(value) else 0
        elif "Analog" in signal_type or "Holding" in signal_type:
            # For analog signals, convert to float
            value = float(value)

        # Update the signal value based on signal type
        # Determine which field to update based on signal type
        if "Digital" in signal_type:
            if hasattr(signal, "digital_value"):
                signal.digital_value = value
            else:
                # Try generic approaches if specific field doesn't exist
                try:
                    signal.db_set("value", value, update_modified=False)
                except Exception as field_error:
                    frappe.logger().error(
                        f"Error setting value field: {str(field_error)}")
                    # Try set() as a fallback
                    signal.set("value", value)
        elif "Analog" in signal_type or "Holding" in signal_type:
            if hasattr(signal, "float_value"):
                signal.float_value = value
            else:
                # Try generic approaches if specific field doesn't exist
                try:
                    signal.db_set("value", value, update_modified=False)
                except Exception as field_error:
                    frappe.logger().error(
                        f"Error setting value field: {str(field_error)}")
                    # Try set() as a fallback
                    signal.set("value", value)
        else:
            # For unknown types, try a generic approach
            try:
                signal.db_set("value", value, update_modified=False)
            except Exception as field_error:
                frappe.logger().error(
                    f"Error setting value field: {str(field_error)}")
                # Try set() as a fallback
                signal.set("value", value)

        signal.save()

        frappe.logger().info(
            f"Successfully updated signal {signal_id} to value {value}")

        # Return success response
        return {
            "status": "success",
            "message": _("Signal value updated successfully"),
            "signal_id": signal_id,
            "value": value
        }

    except Exception as e:
        frappe.logger().error(f"Error in set_signal_value: {str(e)}")
        frappe.log_error(f"Error in set_signal_value: {str(e)}")
        frappe.throw(_("Error setting signal value: {0}").format(str(e)))
        # This will never be reached due to frappe.throw, but satisfies the type checker
        return {"status": "error", "message": str(e)}
