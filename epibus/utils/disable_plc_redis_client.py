import frappe
from frappe.utils import now
import logging

logger = logging.getLogger(__name__)

def disable_redis_client():
    """
    Disable the Redis PLC client by overriding the listen_for_updates function
    to prevent it from scheduling itself again.
    """
    try:
        # Log the disabling of the Redis PLC client
        logger.info(f"Disabling Redis PLC client at {now()}")
        
        # Create a log entry
        frappe.get_doc({
            "doctype": "Error Log",
            "method": "epibus.utils.disable_plc_redis_client.disable_redis_client",
            "error": "Redis PLC client has been disabled in favor of the dedicated PLC worker",
            "error_description": "The Redis PLC client has been disabled to prevent it from running in the short worker queue. The dedicated PLC worker should be used instead."
        }).insert(ignore_permissions=True)
        
        # Override the listen_for_updates function in the plc_redis_client module
        # to prevent it from scheduling itself again
        import epibus.epibus.utils.plc_redis_client as plc_redis_client
        
        # Define a replacement function that does nothing
        def disabled_listen_for_updates(*args, **kwargs):
            logger.info("Redis PLC client listen_for_updates function has been disabled")
            return None
        
        # Replace the original function with our disabled version
        plc_redis_client.listen_for_updates = disabled_listen_for_updates
        
        logger.info("Successfully disabled Redis PLC client")
        return True
        
    except Exception as e:
        logger.error(f"Error disabling Redis PLC client: {str(e)}")
        return False

# Run the function when this module is imported
disable_redis_client()