import frappe
import json
import time
from frappe.realtime import publish_realtime
from epibus.epibus.utils.truthy import truthy,  parse_value
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)

# Import the PLCRedisClient class
from epibus.utils.plc_redis_client import PLCRedisClient

# We'll initialize the client on-demand rather than on import


@frappe.whitelist(allow_guest=True)
def get_signals():
    """Get all Modbus signals for the React dashboard

    Returns the complete Modbus Connection document structure with nested signals
    """
    try:
        # Get connections with nested signals
        client = PLCRedisClient.get_instance()
        connections = client.get_signals()
        return connections

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

        # Parse value based on signal type using our new helper functions
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
                logger.debug(
                    f"📊 Parsed analog value: {value} -> {parsed_value}")
            except (ValueError, TypeError):
                logger.error(f"❌ Error converting {value} to float")
                return {"success": False, "message": f"Cannot convert {value} to a number"}

        logger.info(
            f"🔄 Writing value:{signal.signal_name} ({signal_id}) = {parsed_value} (original: {value})")

        # Write signal
        client = PLCRedisClient.get_instance()
        success = client.write_signal(signal_id, parsed_value)
        
        # Note: The write_signal method now triggers an immediate check for updates
        # This ensures we quickly process any signal changes that result from this command

        if success:
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
        # Request status from PLC bridge
        client = PLCRedisClient.get_instance()
        logger.info("🔄 Requesting PLC Bridge status")
        client.redis.publish("plc:command", json.dumps({
            "command": "status"
        }))
        logger.info("✅ Sent status request to PLC Bridge")

        # Subscribe to the plc:status channel to forward the status to the frontend
        def forward_status_to_frontend(channel, message):
            try:
                logger.info(
                    f"📥 Received PLC status on channel {channel}: {message}")
                status_data = json.loads(message)
                logger.info(f"🔄 Parsed status data: {status_data}")

                # Forward the status to the frontend via Frappe's realtime
                logger.info(f"📤 Publishing status to frontend via realtime")
                publish_realtime('plc:status', status_data)
                logger.info(
                    f"✅ Forwarded PLC status to frontend: {status_data}")
            except Exception as e:
                logger.error(f"❌ Error forwarding PLC status: {str(e)}")
                logger.error(
                    f"Error details: {e.__class__.__name__}: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

        # Set up a temporary subscription to forward the next status message
        pubsub = client.redis.pubsub()
        pubsub.subscribe(**{'plc:status': forward_status_to_frontend})

        # Start a background thread to listen for the status message
        pubsub_thread = pubsub.run_in_thread(sleep_time=1, daemon=True)

        # Schedule the thread to be stopped after a timeout
        def stop_pubsub_thread():
            pubsub_thread.stop()
            pubsub.unsubscribe('plc:status')
            logger.info("✅ Stopped PLC status listener thread")

        # Stop the thread after 5 seconds (timeout)
        frappe.enqueue(stop_pubsub_thread, queue='short',
                       timeout=10, now=False, enqueue_after=5)

        return {"success": True}

    except Exception as e:
        logger.error(f"❌ Error getting PLC status: {str(e)}")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def reload_signals(allow_guest=True):
    """Reload signals in the PLC bridge"""
    try:
        # Request reload from PLC bridge
        client = PLCRedisClient.get_instance()
        client.redis.publish("plc:command", json.dumps({
            "command": "reload_signals"
        }))

        return {"success": True, "message": "Signal reload requested"}

    except Exception as e:
        logger.error(f"❌ Error requesting signal reload: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist(allow_guest=False)
def get_all_signals():
    """Get all signals with their connections in a single call"""
    try:
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
        
        return {
            "success": True,
            "data": connection_data
        }
    except Exception as e:
        logger.error(f"Error getting all signals: {str(e)}")
        return {"success": False, "message": str(e)}

@frappe.whitelist(allow_guest=False)
def signal_update():
    """Handle a signal update from the PLC Bridge"""
    try:
        data = frappe.local.form_dict
        signal_name = data.get("name")
        value = data.get("value")
        
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
            "value": str(value)
        }).insert(ignore_permissions=True)
        
        # Broadcast to Frappe real-time
        frappe.publish_realtime(
            event='modbus_signal_update',
            message={
                'signal': signal_name,
                'signal_name': signal.signal_name,
                'value': value,
                'timestamp': data.get("timestamp", time.time())
            }
        )
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error handling signal update: {str(e)}")
        return {"success": False, "message": str(e)}
