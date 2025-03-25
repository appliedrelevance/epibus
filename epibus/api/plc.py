import frappe
import json
from frappe.realtime import publish_realtime
from epibus.utils.truthy import truthy, parse_value
from epibus.utils.epinomy_logger import get_logger
from epibus.utils.plc_command_handler import handle_plc_command, write_signal as write_signal_command

logger = get_logger(__name__)

@frappe.whitelist(allow_guest=True)
def get_signals():
    """Get all Modbus signals for the React dashboard"""
    try:
        # Get connections with nested signals
        connections = frappe.get_all(
            "Modbus Connection",
            filters={"enabled": 1},
            fields=["name", "device_name", "device_type", "host", "port", "enabled"]
        )
        
        connection_data = []
        
        # Get signals for each connection
        for conn in connections:
            # Get basic signal information
            conn_signals = frappe.get_all(
                "Modbus Signal",
                filters={"parent": conn.name},
                fields=["name", "signal_name", "signal_type", "modbus_address"]
            )
            
            # Process each signal
            processed_signals = []
            for signal in conn_signals:
                try:
                    # Get the full document to access methods and virtual fields
                    signal_doc = frappe.get_doc("Modbus Signal", signal["name"])
                    
                    # Use the document's read_signal method to get the current value
                    try:
                        value = signal_doc.read_signal()
                        signal["value"] = value
                    except Exception as e:
                        logger.warning(f"⚠️ Error reading signal {signal['signal_name']}: {str(e)}")
                        # Fallback to default values based on signal type
                        signal["value"] = False if "Digital" in signal["signal_type"] else 0
                    
                    # Add the PLC address virtual field
                    signal["plc_address"] = signal_doc.get_plc_address()
                    
                except Exception as e:
                    logger.error(f"❌ Error processing signal {signal['name']}: {str(e)}")
                    # Set default values
                    signal["value"] = False if "Digital" in signal["signal_type"] else 0
                    signal["plc_address"] = None
                
                processed_signals.append(signal)
            
            # Add signals to the connection
            conn_data = conn.copy()
            conn_data["signals"] = processed_signals
            connection_data.append(conn_data)
        
        return connection_data
        
    except Exception as e:
        logger.error(f"❌ Error getting signals: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist(allow_guest=True)
def update_signal():
    """Update a signal value from the React dashboard"""
    try:
        # Get parameters
        signal_id = frappe.local.form_dict.get('signal_id')
        value = frappe.local.form_dict.get('value')
        
        logger.info(f"🔄 Received signal update: {signal_id} = {value}")
        
        # Parse value based on signal type
        signal = frappe.get_doc("Modbus Signal", signal_id)
        
        # Use the JavaScript-like parsing
        if "Digital" in signal.get("signal_type", ""):
            # Parse digital values in a JavaScript-like way
            parsed_value = parse_value(value)
            # For digital values, ensure we get a boolean
            if not isinstance(parsed_value, bool):
                parsed_value = truthy(parsed_value)
            logger.debug(f"📊 Parsed digital value: {value} -> {parsed_value}")
        else:
            # For non-digital values, convert to float
            try:
                parsed_value = float(value)
                logger.debug(f"📊 Parsed analog value: {value} -> {parsed_value}")
            except (ValueError, TypeError):
                logger.error(f"❌ Error converting {value} to float")
                return {"success": False, "message": f"Cannot convert {value} to a number"}
        
        logger.info(f"🔄 Writing value:{signal.signal_name} ({signal_id}) = {parsed_value} (original: {value})")
        
        # Write signal using the command handler
        result = write_signal_command(signal_id, parsed_value)
        
        if result.get("success"):
            return {"success": True, "message": f"Updated signal {signal.signal_name}"}
        else:
            return {"success": False, "message": f"Failed to update signal {signal.signal_name}"}
        
    except Exception as e:
        logger.error(f"❌ Error updating signal: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist(allow_guest=True)
def get_plc_status():
    """Get current PLC status"""
    try:
        # Request status from PLC worker
        handle_plc_command({
            "command": "status"
        })
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"❌ Error getting PLC status: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def reload_signals(allow_guest=True):
    """Reload signals in the PLC worker"""
    try:
        # Request reload from PLC worker
        handle_plc_command({
            "command": "reload_signals"
        })
        
        return {"success": True, "message": "Signal reload requested"}
        
    except Exception as e:
        logger.error(f"❌ Error requesting signal reload: {str(e)}")
        return {"success": False, "message": str(e)}
