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
    """Get all Modbus signals for the React dashboard"""
    try:
        # Get signals
        client = PLCRedisClient.get_instance()
        signals = client.get_signals()
        return signals

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


@frappe.whitelist()
def get_plc_status(allow_guest=True):
    """Get current PLC status"""
    try:
        # Request status from PLC bridge
        client = PLCRedisClient.get_instance()
        client.redis.publish("plc:command", json.dumps({
            "command": "status"
        }))

        # Note: We don't wait for response here, status will be published to
        # the 'plc:status' channel and picked up by React directly

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
