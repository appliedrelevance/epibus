import frappe
from frappe import _
from typing import cast
from epibus.epibus.doctype.modbus_signal.modbus_signal import ModbusSignal


def get_context(context):
    """Get page context for the Modbus dashboard."""
    context.no_cache = 1
    context.show_sidebar = True

    # Get initial data
    context.connections = get_modbus_data()

    # Add page metadata
    context.title = _("Modbus Signal Dashboard")
    context.device_types = ["PLC", "Robot", "Simulator", "Other"]
    context.signal_types = [
        "Digital Output Coil",
        "Digital Input Contact",
        "Analog Input Register",
        "Analog Output Register",
        "Holding Register",
    ]


@frappe.whitelist(methods=['GET'])
def get_modbus_data():
    """Get comprehensive data about Modbus connections and their signals."""
    # Fetch Modbus Connection data with all relevant fields
    connections = frappe.get_all(
        "Modbus Connection",
        fields=[
            "name",
            "device_name",
            "device_type",
            "enabled",
            "host",
            "port",
            "thumbnail",
        ],
    )

    # For each connection, fetch its associated signals
    for conn in connections:
        # First get basic signal data
        signal_refs = frappe.get_all(
            "Modbus Signal", filters={"parent": conn.name}, fields=["name"]
        )

        # Then load each signal as a document to get computed fields
        signals = []
        for signal_ref in signal_refs:
            signal_doc = cast(ModbusSignal, frappe.get_doc(
                "Modbus Signal", signal_ref.name))
            signals.append(
                {
                    "name": signal_doc.name,
                    "signal_name": signal_doc.signal_name,
                    "signal_type": signal_doc.signal_type,
                    "modbus_address": signal_doc.modbus_address,
                    "plc_address": signal_doc.get_plc_address(),
                    "value": signal_doc.read_signal(),
                }
            )
        conn["signals"] = signals

    return connections
