# epibus/epibus/api/simulator.py
import frappe
from frappe import _
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)


@frappe.whitelist()
def get_simulators():
    """Get all configured simulators with their current status"""
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
            ],
        )

        logger.debug(f"Retrieved {len(simulators)} simulators")
        return simulators

    except Exception as e:
        logger.error(f"Error retrieving simulators: {str(e)}")
        frappe.throw(_("Failed to retrieve simulators"))


@frappe.whitelist()
def start_simulator(simulator_name):
    """Start a specific simulator"""
    logger.info(f"API: Start request for simulator {simulator_name}")

    try:
        simulator = frappe.get_doc("Modbus Simulator", simulator_name)
        result = simulator.start_simulator()

        if result.get("success"):
            logger.info(f"Successfully started simulator {simulator_name}")
        else:
            logger.error(f"Failed to start simulator: {result.get('error')}")

        return result

    except Exception as e:
        logger.error(f"Error starting simulator {simulator_name}: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def stop_simulator(simulator_name):
    """Stop a specific simulator"""
    logger.info(f"API: Stop request for simulator {simulator_name}")

    try:
        simulator = frappe.get_doc("Modbus Simulator", simulator_name)
        result = simulator.stop_simulator()

        if result.get("success"):
            logger.info(f"Successfully stopped simulator {simulator_name}")
        else:
            logger.error(f"Failed to stop simulator: {result.get('error')}")

        return result

    except Exception as e:
        logger.error(f"Error stopping simulator {simulator_name}: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_io_points(simulator_name):
    """Get all I/O points for a simulator"""
    try:
        points = frappe.get_all(
            "Modbus Signal",
            filters={"parent": simulator_name},
            fields=[
                "signal_name",
                "signal_type",
                "modbus_address",
                "plc_address",
                "digital_value",
                "float_value",
            ],
        )

        logger.debug(f"Retrieved {len(points)} I/O points for {simulator_name}")
        return points

    except Exception as e:
        logger.error(f"Error getting I/O points for {simulator_name}: {str(e)}")
        return []
