# -*- coding: utf-8 -*-
# Copyright (c) 2023, Applied Relevance and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from epibus.epibus.doctype.modbus_signal.modbus_signal import ModbusSignal
from epibus.epibus.doctype.modbus_connection.modbus_connection import ModbusConnection
import frappe
from frappe import _
from frappe.utils import cint
import json
from typing import Dict, List, Any, Optional, cast, TypedDict

from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)

# Cache to store the last known values of signals
# This will persist between function calls
signal_value_cache = {}


class ModbusConnectionDict(TypedDict):
    name: str
    device_name: str
    device_type: str
    host: str
    port: int
    enabled: int
    signals: List['ModbusSignalDict']


class ModbusSignalDict(TypedDict):
    name: str
    signal_name: str
    signal_type: str
    modbus_address: int
    value: Optional[Any]


# Import the ModbusSignal class

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

    # Only log at debug level for dashboard access
    logger.debug(
        f"Warehouse dashboard accessed by user: {frappe.session.user}")
    logger.debug(
        f"CSRF token for session: {frappe.session.csrf_token[:5]}...")

    return context


@frappe.whitelist()
def get_modbus_data() -> List[ModbusConnectionDict]:
    """
    Get all Modbus connections and their signals.
    Uses the current user's permissions to access the data.

    Returns:
        List[ModbusConnectionDict]: A list of Modbus connections with their signals.
    """
    try:
        # Log the current user for debugging
        current_user = frappe.session.user
        logger.debug(f"Fetching Modbus data as user: {current_user}")

        # Get all enabled Modbus connections
        connections: List[ModbusConnectionDict] = frappe.get_all(
            "Modbus Connection",
            fields=["name", "device_name", "device_type",
                    "host", "port", "enabled"],
            filters={"enabled": 1},
            order_by="device_name asc"
        )

        logger.debug(f"Found {len(connections)} Modbus connections")

        # For each connection, get its signals
        for connection in connections:
            # Get signals without the 'value' field which doesn't exist in the table
            signals: List[ModbusSignalDict] = frappe.get_all(
                "Modbus Signal",
                fields=["name", "signal_name",
                        "signal_type", "modbus_address"],
                filters={"parent": connection["name"]},
                order_by="signal_name asc"
            )

            # Get the device document for direct reading if needed
            device_doc = None

            # For each signal, get the actual document to access its current value
            for signal in signals:
                try:
                    # Get the full signal document to access its current value
                    signal_doc = cast(ModbusSignal, frappe.get_doc(
                        "Modbus Signal", signal["name"]))

                    # The actual value might be stored in different fields based on signal type
                    # Add the current value to the signal object
                    if hasattr(signal_doc, "current_value") and getattr(signal_doc, "current_value", None) is not None:
                        signal["value"] = getattr(signal_doc, "current_value")
                    elif hasattr(signal_doc, "float_value") and getattr(signal_doc, "float_value", None) is not None:
                        signal["value"] = getattr(signal_doc, "float_value")
                    elif hasattr(signal_doc, "digital_value") and getattr(signal_doc, "digital_value", None) is not None:
                        signal["value"] = getattr(signal_doc, "digital_value")
                    else:
                        # Try to read the value directly from the device if database values are null
                        try:
                            # Initialize device_doc only if needed
                            if device_doc is None:
                                device_doc = cast(ModbusConnection, frappe.get_doc(
                                    "Modbus Connection", connection["name"]))

                            # Read the signal value directly
                            logger.debug(
                                f"Attempting to read signal {signal['name']} directly from device {connection['name']}")

                            # Use the read_signal method to get the current value
                            # We've already cast signal_doc to ModbusSignal, so this is safe
                            value = signal_doc.read_signal()

                            # Get previous value from our persistent cache
                            signal_id = signal['name']
                            previous_value = signal_value_cache.get(signal_id)

                            if value is not None:
                                signal["value"] = value
                                # No need to update the database for virtual fields
                                # The value is already stored in the signal dictionary for the UI

                                # Only log if the value has changed from the cached value
                                if previous_value != value:
                                    # Get the human-readable signal name
                                    signal_name = signal['signal_name']
                                    logger.info(
                                        f"Signal value changed: {signal_name} ({signal_id}) from {previous_value} to {value}")

                                # Update the cache with the new value
                                signal_value_cache[signal_id] = value
                            else:
                                signal["value"] = None
                                # Get the human-readable signal name
                                signal_name = signal['signal_name']
                                logger.warning(
                                    f"Direct read returned None for signal {signal_name} ({signal_id})")
                        except Exception as read_error:
                            # Get the human-readable signal name
                            signal_name = signal['signal_name']
                            logger.error(
                                f"Error reading signal {signal_name} ({signal['name']}) directly: {str(read_error)}")
                            signal["value"] = None

                    # Debug level for all signal values
                    logger.debug(
                        f"Signal {signal['name']} value: {signal.get('value')}")
                except Exception as signal_error:
                    # Get the human-readable signal name
                    signal_name = signal['signal_name']
                    logger.error(
                        f"Error getting value for signal {signal_name} ({signal['name']}): {str(signal_error)}")
                    signal["value"] = None

            # Add signals to the connection
            connection["signals"] = signals
            logger.debug(
                f"Connection {connection['name']} has {len(signals)} signals")

        return connections

    except Exception as e:
        logger.error(f"Error in get_modbus_data: {str(e)}")
        frappe.log_error(f"Error in get_modbus_data: {str(e)}")
        frappe.throw(_("Error fetching Modbus data: {0}").format(str(e)))
        return []  # This will never be reached due to frappe.throw, but satisfies the type checker


@frappe.whitelist()
def set_signal_value(signal_id: str, value: Any) -> Dict[str, Any]:
    """
    Set the value of a Modbus signal using direct Modbus API calls.
    Uses the current user's permissions to update the signal.
    
    This function handles type conversion based on the signal type and
    provides proper error handling for Modbus API communication.

    Args:
        signal_id (str): The ID of the signal to update.
        value (Any): The new value for the signal.

    Returns:
        Dict[str, Any]: A dictionary with the status of the operation,
                        including the actual value read back from the device.
    """
    try:
        # Log the current user for debugging
        current_user = frappe.session.user
        logger.debug(
            f"Setting signal value as user: {current_user} for signal: {signal_id}")

        # Get the signal document to determine its type
        signal = cast(ModbusSignal, frappe.get_doc("Modbus Signal", signal_id))
        signal_type = signal.signal_type
        signal_name = signal.signal_name

        # Convert value to the appropriate type based on signal type
        if "Digital" in signal_type:
            # For digital signals, convert to boolean
            # Using bool(cint(value)) to ensure proper boolean conversion
            # This avoids type mismatch when passing to write_signal
            value = bool(cint(value))
        elif "Analog" in signal_type or "Holding" in signal_type:
            # For analog signals, convert to float
            value = float(value)

        # Get the current value from our cache
        previous_value = signal_value_cache.get(signal_id)

        # If not in cache, try to get from signal attributes
        if previous_value is None:
            if hasattr(signal, "current_value") and getattr(signal, "current_value", None) is not None:
                previous_value = getattr(signal, "current_value")
            elif hasattr(signal, "float_value") and getattr(signal, "float_value", None) is not None:
                previous_value = getattr(signal, "float_value")
            elif hasattr(signal, "digital_value") and getattr(signal, "digital_value", None) is not None:
                previous_value = getattr(signal, "digital_value")

        # Use the write_signal method directly to update the value via Modbus API
        logger.info(f"Writing signal {signal_name} ({signal_id}) via Modbus API...")
        
        try:
            # Execute the write operation
            result_value = signal.write_signal(value)
            
            # Update our cache with the new value
            signal_value_cache[signal_id] = result_value
            
            # Log the value change at INFO level
            logger.info(
                f"Signal value changed: {signal_name} ({signal_id}) from {previous_value} to {result_value}")
            
            # Return success response with the actual value read back from the device
            return {
                "status": "success",
                "message": _("Signal value updated successfully via Modbus API"),
                "signal_id": signal_id,
                "value": result_value
            }
        except Exception as api_error:
            # Log the specific API error
            logger.error(f"Modbus API error for signal {signal_name} ({signal_id}): {str(api_error)}")
            # Re-raise the exception to be caught by the outer try-except block
            raise

    except Exception as e:
        # Log the error with more context
        error_msg = f"Error in set_signal_value for signal {signal_id}: {str(e)}"
        logger.error(error_msg)
        frappe.log_error(error_msg, "Modbus API Error")
        
        # Provide a more user-friendly error message
        frappe.throw(_("Error setting signal value via Modbus API: {0}").format(str(e)))
        
        # This will never be reached due to frappe.throw, but satisfies the type checker
        return {
            "status": "error",
            "message": str(e),
            "signal_id": signal_id,
            "value": None
        }


@frappe.whitelist()
def clear_signal_value_cache() -> Dict[str, Any]:
    """
    Clear the in-memory cache of signal values.
    This is useful for debugging or forcing a refresh of all values.

    Returns:
        Dict[str, Any]: A dictionary with the status of the operation.
    """
    try:
        # Log the current user for debugging
        current_user = frappe.session.user
        logger.debug(f"Clearing signal value cache as user: {current_user}")

        # Store the cache size for logging
        cache_size = len(signal_value_cache)

        # Clear the cache
        signal_value_cache.clear()

        logger.info(
            f"Signal value cache cleared. {cache_size} entries removed.")

        # Return success response
        return {
            "status": "success",
            "message": _("Signal value cache cleared successfully"),
            "entries_removed": cache_size
        }

    except Exception as e:
        logger.error(f"Error in clear_signal_value_cache: {str(e)}")
        frappe.log_error(f"Error in clear_signal_value_cache: {str(e)}")
        frappe.throw(
            _("Error clearing signal value cache: {0}").format(str(e)))
        # This will never be reached due to frappe.throw, but satisfies the type checker
        return {"status": "error", "message": str(e)}
