import frappe
from frappe import _
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)

@frappe.whitelist()
def get_simulators():
    """Get all configured simulators
    
    Returns:
        list: List of simulator documents
    """
    try:
        simulators = frappe.get_all(
            "Modbus Simulator",
            fields=[
                "name", 
                "simulator_name",
                "equipment_type",
                "connection_status",
                "server_port",
                "enabled",
                "last_status_update"
            ]
        )
        logger.debug(f"Retrieved {len(simulators)} simulators")
        return simulators
        
    except Exception as e:
        logger.error(f"Error retrieving simulators: {str(e)}")
        frappe.throw(_("Failed to retrieve simulators"))

@frappe.whitelist()
def start_simulator(simulator_name):
    """Start a specific simulator
    
    Args:
        simulator_name (str): Name of simulator to start
        
    Returns:
        dict: Status of operation
    """
    try:
        simulator = frappe.get_doc("Modbus Simulator", simulator_name)
        return simulator.start_simulator()
        
    except Exception as e:
        logger.error(f"Error starting simulator {simulator_name}: {str(e)}")
        frappe.throw(_("Failed to start simulator"))

@frappe.whitelist()
def stop_simulator(simulator_name):
    """Stop a specific simulator
    
    Args:
        simulator_name (str): Name of simulator to stop
        
    Returns:
        dict: Status of operation
    """
    try:
        simulator = frappe.get_doc("Modbus Simulator", simulator_name)
        return simulator.stop_simulator()
        
    except Exception as e:
        logger.error(f"Error stopping simulator {simulator_name}: {str(e)}")
        frappe.throw(_("Failed to stop simulator"))

@frappe.whitelist()
def get_io_points(simulator_name):
    """Get all I/O points for a simulator
    
    Args:
        simulator_name (str): Name of simulator to get points for
        
    Returns:
        list: List of I/O point configurations
    """
    try:
        simulator = frappe.get_doc("Modbus Simulator", simulator_name)
        return simulator.get_io_points()
        
    except Exception as e:
        logger.error(f"Error getting I/O points for {simulator_name}: {str(e)}")
        frappe.throw(_("Failed to retrieve I/O points"))

@frappe.whitelist()
def get_server_status(simulator_name):
    """Get status of a simulator server
    
    Args:
        simulator_name (str): Name of simulator to check
        
    Returns:
        dict: Server status details
    """
    try:
        simulator = frappe.get_doc("Modbus Simulator", simulator_name)
        return {
            "running": simulator._running,
            "port": simulator.server_port,
            "status": simulator.connection_status
        }
    except Exception as e:
        logger.error(f"Error getting server status for {simulator_name}: {str(e)}")
        frappe.throw(_("Failed to get simulator status"))