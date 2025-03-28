import frappe
import json
import time
from frappe.realtime import publish_realtime
from epibus.epibus.utils.truthy import truthy, parse_value
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.doctype.modbus_event.modbus_event import ModbusEvent

logger = get_logger(__name__)

@frappe.whitelist(allow_guest=True)
def get_signals():
    """Get all Modbus signals for the React dashboard
    
    Returns the complete Modbus Connection document structure with nested signals
    """
    try:
        # This function now uses the same implementation as get_all_signals
        # but formats the response to match what the frontend expects
        connections_data = get_all_signals_internal()
        
        if not connections_data.get("success", False):
            return {"success": False, "message": connections_data.get("message", "Unknown error")}
            
        return connections_data.get("data", [])

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

        # Parse value based on signal type using our helper functions
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

        logger.info(f"🔄 Writing value: {signal.signal_name} ({signal_id}) = {parsed_value} (original: {value})")

        # Write signal directly using the signal's write_signal method
        success = signal.write_signal(parsed_value)
        
        if success:
            # Publish update to realtime for immediate feedback
            publish_realtime(
                event='modbus_signal_update',
                message={
                    'signal': signal_id,
                    'signal_name': signal.signal_name,
                    'value': parsed_value,
                    'timestamp': time.time(),
                    'source': 'write_request'
                }
            )
            
            # Log the update
            frappe.get_doc({
                "doctype": "Modbus Event",
                "event_type": "Signal Update",
                "connection": signal.parent,
                "signal": signal_id,
                "new_value": str(parsed_value),
                "message": f"Signal {signal.signal_name} updated to {parsed_value} via API"
            }).insert(ignore_permissions=True)
            
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
        # Check if any Modbus connections are enabled and connected
        connections = frappe.get_all(
            "Modbus Connection",
            filters={"enabled": 1},
            fields=["name", "device_name", "host", "port"]
        )
        
        # Default status
        status = {
            "connected": False,
            "connections": [],
            "timestamp": time.time()
        }
        
        # Check each connection
        for conn in connections:
            try:
                # Get a signal from this connection to test
                signals = frappe.get_all(
                    "Modbus Signal",
                    filters={"parent": conn.name},
                    limit=1
                )
                
                if signals:
                    signal_doc = frappe.get_doc("Modbus Signal", signals[0].name)
                    # Try to read the signal to test connection
                    try:
                        signal_doc.read_signal()
                        conn_status = True
                    except Exception:
                        conn_status = False
                else:
                    conn_status = False
                    
                status["connections"].append({
                    "name": conn.name,
                    "device_name": conn.device_name,
                    "connected": conn_status
                })
                
                # If any connection is working, set overall status to connected
                if conn_status:
                    status["connected"] = True
                    
            except Exception as conn_error:
                logger.error(f"❌ Error checking connection {conn.name}: {str(conn_error)}")
                status["connections"].append({
                    "name": conn.name,
                    "device_name": conn.device_name,
                    "connected": False,
                    "error": str(conn_error)
                })
        
        # Publish status to frontend
        publish_realtime('plc:status', status)
        
        return {"success": True, "status": status}

    except Exception as e:
        logger.error(f"❌ Error getting PLC status: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def reload_signals(allow_guest=True):
    """Reload signals in the PLC bridge"""
    try:
        # Clear any caches
        frappe.cache().delete_key("modbus_signals")
        
        # Get fresh data from the database
        connections_data = get_all_signals_internal()
        
        # Publish an event to notify clients that signals have been reloaded
        publish_realtime(
            event='signals_reloaded',
            message={"timestamp": time.time()}
        )
        
        return {"success": True, "message": "Signals reloaded successfully"}

    except Exception as e:
        logger.error(f"❌ Error reloading signals: {str(e)}")
        return {"success": False, "message": str(e)}

def get_all_signals_internal():
    """Internal function to get all signals with their connections
    
    This is used by both get_signals() and get_all_signals() to avoid code duplication
    """
    try:
        # Check if we have cached data
        cached_data = frappe.cache().get_value("modbus_signals")
        if cached_data:
            return cached_data
            
        # Get enabled Modbus Connections with all fields
        connections = frappe.get_all(
            "Modbus Connection",
            filters={"enabled": 1},
            fields=["name", "device_name", "device_type", "host", "port", "enabled"]
        )
        
        # Initialize connections list with signals
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
        
        result = {
            "success": True,
            "data": connection_data
        }
        
        # Cache the result for a short time (10 seconds)
        frappe.cache().set_value("modbus_signals", result, expires_in_sec=10)
        
        return result
    except Exception as e:
        logger.error(f"Error getting all signals: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist(allow_guest=False)
def get_all_signals():
    """Get all signals with their connections in a single call"""
    return get_all_signals_internal()

@frappe.whitelist(allow_guest=False)
def signal_update():
    """Handle a signal update from the PLC Bridge"""
    try:
        data = frappe.local.form_dict
        signal_name = data.get("name")
        value = data.get("value")
        timestamp = data.get("timestamp", time.time())
        
        if not signal_name or value is None:
            return {"success": False, "message": "Invalid signal update"}
        
        # Get signal document
        if not frappe.db.exists("Modbus Signal", signal_name):
            return {"success": False, "message": f"Signal {signal_name} not found"}
        
        signal = frappe.get_doc("Modbus Signal", signal_name)
        
        # Log the update
        frappe.get_doc({
            "doctype": "Modbus Event",
            "event_type": "Signal Update",
            "connection": signal.parent,
            "signal": signal_name,
            "new_value": str(value),
            "message": f"Signal {signal.signal_name} updated to {value} via PLC Bridge"
        }).insert(ignore_permissions=True)
        
        # Find and process actions triggered by this signal
        process_signal_actions(signal_name, value)
        
        # Broadcast to Frappe real-time
        publish_realtime(
            event='modbus_signal_update',
            message={
                'signal': signal_name,
                'signal_name': signal.signal_name,
                'value': value,
                'timestamp': timestamp,
                'source': 'plc_bridge'
            }
        )
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error handling signal update: {str(e)}")
        return {"success": False, "message": str(e)}

def process_signal_actions(signal_name, value):
    """Process actions triggered by a signal update"""
    try:
        # Find applicable actions with direct signal link
        actions = frappe.get_all(
            "Modbus Action",
            filters={
                "modbus_signal": signal_name,
                "enabled": 1,
                "trigger_type": "Signal Change"
            },
            fields=["name", "signal_condition", "signal_value", "server_script"]
        )
        
        logger.info(f"Found {len(actions)} potential actions for signal {signal_name}")
        
        # Process each action based on condition
        for action in actions:
            try:
                # Check if condition is met
                condition_met = False
                condition_desc = "unknown"
                
                if not action.signal_condition or action.signal_condition == "Any Change":
                    condition_met = True
                    condition_desc = "any change"
                elif action.signal_condition == "Equals":
                    try:
                        # Handle different value types
                        if isinstance(value, bool):
                            # Boolean comparison
                            target_value = action.signal_value.lower() == "true"
                            condition_met = value == target_value
                        elif "." in action.signal_value:
                            # Float comparison
                            target_value = float(action.signal_value)
                            condition_met = float(value) == target_value
                        else:
                            # Integer comparison
                            target_value = int(action.signal_value)
                            condition_met = int(value) == target_value
                        
                        condition_desc = f"equals {target_value}"
                    except (ValueError, TypeError):
                        # Handle conversion errors
                        logger.warning(f"⚠️ Invalid value comparison: {value} == {action.signal_value}")
                        # Fall back to string comparison
                        condition_met = str(value) == action.signal_value
                        condition_desc = f"string equals {action.signal_value}"
                
                elif action.signal_condition == "Greater Than":
                    try:
                        target_value = float(action.signal_value)
                        condition_met = float(value) > target_value
                        condition_desc = f"greater than {target_value}"
                    except (ValueError, TypeError):
                        logger.error(f"❌ Invalid comparison for non-numeric value: {value} > {action.signal_value}")
                
                elif action.signal_condition == "Less Than":
                    try:
                        target_value = float(action.signal_value)
                        condition_met = float(value) < target_value
                        condition_desc = f"less than {target_value}"
                    except (ValueError, TypeError):
                        logger.error(f"❌ Invalid comparison for non-numeric value: {value} < {action.signal_value}")
                
                # Execute action if condition is met
                if condition_met:
                    logger.info(f"✅ Condition met for action {action.name}: {condition_desc}")
                    
                    # Execute action
                    execute_action(action.name, signal_name, value, condition_desc)
                else:
                    logger.debug(f"⏭️ Condition not met for action {action.name}: {condition_desc}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing action {action.name}: {str(e)}")
                
    except Exception as e:
        logger.error(f"❌ Error processing signal actions: {str(e)}")

def execute_action(action_name, signal_name, value, condition_desc=None):
    """Execute a Modbus Action"""
    try:
        # Get the action document
        action_doc = frappe.get_doc("Modbus Action", action_name)
        
        # Get the signal document
        signal_doc = frappe.get_doc("Modbus Signal", signal_name)
        
        # Get the parent connection
        connection_doc = frappe.get_doc("Modbus Connection", signal_doc.parent)
        
        # Setup context for the script
        frappe.flags.modbus_context = {
            "action": action_doc,
            "connection": connection_doc,
            "signal": signal_doc,
            "value": value,
            "params": {p.parameter: p.value for p in action_doc.parameters},
            "logger": logger  # Provide logger to scripts
        }
        
        # Log the action execution start
        logger.info(f"🔄 Executing action {action_name} for signal {signal_name} = {value}")
        if condition_desc:
            logger.info(f"Trigger condition: {condition_desc}")
        
        # Execute the script
        result = None
        if action_doc.server_script:
            script_doc = frappe.get_doc("Server Script", action_doc.server_script)
            result = script_doc.execute_method()
            
            # Log the execution
            frappe.get_doc({
                "doctype": "Modbus Event",
                "event_type": "Action Execution",
                "connection": connection_doc.name,
                "signal": signal_name,
                "action": action_name,
                "new_value": str(value),
                "status": "Success",
                "message": f"Successfully executed action '{action_name}' for signal '{signal_name}' with value {value}"
            }).insert(ignore_permissions=True)
        
        # Clear context
        frappe.flags.modbus_context = None
        
        logger.info(f"✅ Executed action {action_name} successfully")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error executing action {action_name}: {str(e)}")
        
        # Log the error
        try:
            frappe.get_doc({
                "doctype": "Modbus Event",
                "event_type": "Action Execution",
                "connection": connection_doc.name if 'connection_doc' in locals() else None,
                "signal": signal_name,
                "action": action_name,
                "new_value": str(value) if 'value' in locals() else None,
                "status": "Failed",
                "error_message": str(e),
                "message": f"Failed to execute action '{action_name}' for signal '{signal_name}': {str(e)}"
            }).insert(ignore_permissions=True)
        except Exception as log_error:
            logger.error(f"❌ Error logging action failure: {str(log_error)}")
        frappe.log_error(f"Error executing Modbus Action {action_name}: {str(e)}")
        return {"success": False, "error": str(e)}

@frappe.whitelist(allow_guest=True)
def log_event():
    """Log an event from the PLC Bridge
    
    This endpoint is called by the PLC Bridge to log events to Frappe.
    It maps the event_data fields to the ModbusEvent.log_event parameters.
    """
    try:
        # Get the event data from the request
        event_data = frappe.local.form_dict
        if isinstance(event_data, str):
            event_data = json.loads(event_data)
            
        # Extract fields from event_data
        event_type = event_data.get('event_type')
        status = event_data.get('status', 'Success')
        signal = event_data.get('signal')
        action = event_data.get('action')
        message = event_data.get('message')
        
        # Get the signal document to find its parent connection (device)
        device = None
        if signal:
            try:
                signal_doc = frappe.get_doc("Modbus Signal", signal)
                device = signal_doc.parent
            except Exception as e:
                logger.warning(f"Could not get device for signal {signal}: {str(e)}")
        
        # If we couldn't get the device from the signal, use a default
        if not device:
            device = "Unknown Device"
        
        # Log the event using the ModbusEvent.log_event method
        ModbusEvent.log_event(
            event_type=event_type,
            device=device,
            status=status,
            signal=signal,
            action=action,
            message=message
        )
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error logging event: {str(e)}")
        return {"success": False, "message": str(e)}
        return {"success": False, "error": str(e)}
