import frappe
import json
from frappe.realtime import publish_realtime
import logging

# Set up logger
logger = logging.getLogger(__name__)

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

        if not signal_id:
            return {"success": False, "message": "Signal ID is required"}

        # Parse value based on signal type
        signal = frappe.get_doc("Modbus Signal", signal_id)
        if "Digital" in signal.get("signal_type", ""):
            value = value.lower() == "true" if isinstance(value, str) else bool(value)
        else:
            value = float(value)

        logger.info(f"🔄 Received signal update: {signal_id} = {value}")

        # Write signal
        client = PLCRedisClient.get_instance()
        success = client.write_signal(signal_id, value)

        if success:
            return {"success": True, "message": f"Updated signal {signal_id}"}
        else:
            return {"success": False, "message": f"Failed to update signal {signal_id}"}

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
