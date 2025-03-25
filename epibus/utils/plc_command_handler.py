import frappe
import json
from epibus.utils.plc_worker_job import start_plc_worker

def handle_plc_command(command_data):
    """Handle PLC commands from the frontend"""
    try:
        # If we have a local PLC worker, use it directly
        if hasattr(frappe.local, 'plc_worker'):
            frappe.local.plc_worker.handle_command(command_data)
        else:
            # Otherwise, publish to the realtime system for the worker to pick up
            frappe.publish_realtime(
                event='plc_command',
                message=command_data
            )
    except Exception as e:
        frappe.logger().error(f"❌ Error handling PLC command: {str(e)}")

@frappe.whitelist()
def write_signal(signal_name, value):
    """Write a signal value to the PLC"""
    try:
        # Convert value to appropriate type
        if isinstance(value, str):
            if value.lower() in ('true', 'yes', '1'):
                value = True
            elif value.lower() in ('false', 'no', '0'):
                value = False
            else:
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass
        
        # Send command
        handle_plc_command({
            "command": "write_signal",
            "signal": signal_name,
            "value": value
        })
        
        return {"success": True}
    except Exception as e:
        frappe.logger().error(f"❌ Error in write_signal: {str(e)}")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def reload_signals():
    """Reload signals from the database"""
    try:
        handle_plc_command({
            "command": "reload_signals"
        })
        
        return {"success": True}
    except Exception as e:
        frappe.logger().error(f"❌ Error in reload_signals: {str(e)}")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_plc_status():
    """Get the status of the PLC connection"""
    try:
        handle_plc_command({
            "command": "status"
        })
        
        return {"success": True}
    except Exception as e:
        frappe.logger().error(f"❌ Error in get_plc_status: {str(e)}")
        return {"success": False, "error": str(e)}