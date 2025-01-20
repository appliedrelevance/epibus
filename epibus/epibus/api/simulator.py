import frappe
from frappe import _
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)


@frappe.whitelist()
def get_simulators():
    """Get all configured simulators with their current status

    Returns:
        list: List of simulator documents with mapped fields
    """
    try:
        simulators = frappe.get_all(
            "Modbus Simulator",
            fields=[
                "name",
                "simulator_name",
                "equipment_type",
                "server_status",
                "server_port",
                "enabled",
                "last_status_update",
                "error_message",  # Added for error handling
            ],
        )

        # Map IO points for each simulator
        for simulator in simulators:
            io_points = frappe.get_all(
                "Modbus Signal",
                filters={"parent": simulator.name},
                fields=[
                    "signal_name",
                    "signal_type",
                    "modbus_address",
                    "plc_address",
                    "digital_value",
                    "float_value",
                ],
            )
            simulator["io_points"] = io_points

        logger.debug(f"Retrieved {len(simulators)} simulators")
        return simulators

    except Exception as e:
        logger.error(f"Error retrieving simulators: {str(e)}")
        frappe.throw(_("Failed to retrieve simulators"))
