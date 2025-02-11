import frappe
from frappe import _


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
        "Holding Register"
    ]


@frappe.whitelist()
def get_modbus_data():
    """Get comprehensive data about Modbus connections and their signals."""
    # Fetch Modbus Connection data with all relevant fields
    connections = frappe.get_all(
        "Modbus Connection",
        fields=[
            "name", "device_name", "device_type", "enabled",
            "host", "port", "thumbnail"
        ]
    )

    # For each connection, fetch its associated signals
    for conn in connections:
        signals = frappe.get_all(
            "Modbus Signal",
            filters={"parent": conn.name},
            fields=[
                "name", "signal_name", "signal_type", "modbus_address"
            ]
        )
        conn["signals"] = signals

    return connections
