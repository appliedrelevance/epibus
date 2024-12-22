import frappe
from frappe import _
from epibus.epibus.doctype.plc_simulator.plc_simulator import PLCSimulator

@frappe.whitelist()
def get_simulators():
    """Get all enabled simulators"""
    try:
        simulators = frappe.get_all(
            "PLC Simulator",
            filters={"enabled": 1},
            fields=["name", "connection_status", "server_port"]
        )
        return [{"name": sim.name, "status": sim.connection_status, "port": sim.server_port} for sim in simulators]
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Simulators Error")
        return {'error': str(e)}


@frappe.whitelist()
def get_server_status(simulator_name=None):
    """Get the current status of the PLC simulator server"""
    try:
        if simulator_name:
            simulator = frappe.get_doc("PLC Simulator", simulator_name)
            return {
                'running': simulator._running if hasattr(simulator, '_running') else False,
                'status': simulator.connection_status,
                'port': simulator.server_port
            }
        else:
            # Get all enabled simulators
            simulators = frappe.get_all(
                "PLC Simulator",
                filters={"enabled": 1},
                fields=["name", "connection_status", "server_port"]
            )
            return [{"name": sim.name, "status": sim.connection_status, "port": sim.server_port} for sim in simulators]
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Simulator Status Error")
        return {'error': str(e)}

@frappe.whitelist()
def start_simulator(simulator_name):
    """Start a specific PLC simulator instance"""
    try:
        simulator = frappe.get_doc("PLC Simulator", simulator_name)
        if simulator.start_simulator():
            return {'success': True, 'message': f'Simulator {simulator_name} started successfully'}
        return {'success': False, 'message': 'Failed to start simulator'}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Start Simulator Error")
        return {'error': str(e)}

@frappe.whitelist()
def stop_simulator(simulator_name):
    """Stop a specific PLC simulator instance"""
    try:
        simulator = frappe.get_doc("PLC Simulator", simulator_name)
        if simulator.stop_simulator():
            return {'success': True, 'message': f'Simulator {simulator_name} stopped successfully'}
        return {'success': False, 'message': 'Failed to stop simulator'}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Stop Simulator Error")
        return {'error': str(e)}

@frappe.whitelist()
def get_io_points(simulator_name):
    """Get all I/O points for a specific simulator"""
    try:
        simulator = frappe.get_doc("PLC Simulator", simulator_name)
        points = simulator.get_io_points()
        return points
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get IO Points Error")
        return {'error': str(e)}

@frappe.whitelist()
def set_output(address, value, simulator_name=None):
    """Set a digital output value"""
    try:
        # If simulator_name not provided, get first enabled simulator
        if not simulator_name:
            simulator = frappe.get_all(
                "PLC Simulator",
                filters={"enabled": 1},
                limit=1
            )
            if not simulator:
                return {'error': 'No enabled simulator found'}
            simulator_name = simulator[0].name

        simulator = frappe.get_doc("PLC Simulator", simulator_name)
        if simulator._set_output(int(address), bool(int(value))):
            return {'success': True, 'message': f'Output {address} set to {value}'}
        return {'success': False, 'message': 'Failed to set output'}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Set Output Error")
        return {'error': str(e)}

@frappe.whitelist()
def set_input(address, value, simulator_name=None):
    """Set a digital input value"""
    try:
        if not simulator_name:
            simulator = frappe.get_all(
                "PLC Simulator",
                filters={"enabled": 1},
                limit=1
            )
            if not simulator:
                return {'error': 'No enabled simulator found'}
            simulator_name = simulator[0].name

        simulator = frappe.get_doc("PLC Simulator", simulator_name)
        if simulator._set_input(int(address), bool(int(value))):
            return {'success': True, 'message': f'Input {address} set to {value}'}
        return {'success': False, 'message': 'Failed to set input'}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Set Input Error")
        return {'error': str(e)}

@frappe.whitelist()
def set_register(address, value, simulator_name=None):
    """Set a register value"""
    try:
        if not simulator_name:
            simulator = frappe.get_all(
                "PLC Simulator",
                filters={"enabled": 1},
                limit=1
            )
            if not simulator:
                return {'error': 'No enabled simulator found'}
            simulator_name = simulator[0].name

        simulator = frappe.get_doc("PLC Simulator", simulator_name)
        if simulator._set_register(int(address), int(value)):
            return {'success': True, 'message': f'Register {address} set to {value}'}
        return {'success': False, 'message': 'Failed to set register value'}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Set Register Error")
        return {'error': str(e)}