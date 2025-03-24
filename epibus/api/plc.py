import frappe
import json
from frappe.realtime import publish_realtime
from epibus.epibus.utils.truthy import truthy,  parse_value
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)

# Initialize the Redis client when this module is imported
try:
    # Import the PLCRedisClient class
    from epibus.utils.plc_redis_client import PLCRedisClient

    redis_client = PLCRedisClient.get_instance()
    logger.info("✅ Redis client initialized on import")
except Exception as e:
    logger.error(f"❌ Error initializing Redis client on import: {str(e)}")


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
