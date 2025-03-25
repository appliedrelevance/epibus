import json
import redis
import frappe
import time
from typing import Dict, Any, List, Optional, Union
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)


class PLCRedisClient:
    """Redis client for communicating with the PLC bridge"""

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = PLCRedisClient()
        return cls._instance

    def __init__(self):
        """Initialize Redis client"""
        settings = frappe.get_doc("Modbus Settings")

        # Get Redis settings from site_config.json
        try:
            redis_config = frappe.get_site_config().get('redis_queue')

            # Default to redis-queue:6379 if not found in config
            if not redis_config:
                logger.warning(
                    "⚠️ redis_queue not found in site_config.json, using default redis-queue:6379")
                host = 'redis-queue'
                port = 6379
            elif isinstance(redis_config, str) and redis_config.startswith('redis://'):
                # Parse redis URL (format: redis://hostname:port)
                parts = redis_config.replace('redis://', '').split(':')
                host = parts[0]
                port = int(parts[1]) if len(parts) > 1 else 6379
            else:
                # Use dictionary format
                host = redis_config.get('host', 'redis-queue')
                port = redis_config.get('port', 6379)
        except Exception as e:
            logger.error(
                f"❌ Error reading Redis config: {str(e)}, using default redis-queue:6379")
            host = 'redis-queue'
            port = 6379

        logger.info(f"🔌 Connecting to Redis at {host}:{port}")

        # Initialize Redis client
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=0
        )

        # Initialize Redis pubsub
        self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)

        # Start pubsub listener
        self._start_listener()

        logger.info("🔌 Initialized PLC Redis client")

    def _start_listener(self):
        """Start Redis pubsub listener"""
        # This method has been disabled as the Redis PLC client has been replaced by the dedicated PLC worker
        logger.info("⚠️ Redis PLC client _start_listener has been disabled - using dedicated PLC worker instead")
        return
            
    def _schedule_periodic_listener(self):
        """Schedule periodic checks for updates"""
        # This method has been disabled as the Redis PLC client has been replaced by the dedicated PLC worker
        logger.info("⚠️ Redis PLC client scheduling has been disabled - using dedicated PLC worker instead")
        return
            
    def trigger_immediate_check(self):
        """Trigger an immediate check for updates
        
        This method has been disabled as the Redis PLC client has been replaced by the dedicated PLC worker.
        """
        logger.info("⚠️ Redis PLC client trigger_immediate_check has been disabled - using dedicated PLC worker instead")
        return

    def get_signals(self) -> List[Dict[str, Any]]:
        """Get all Modbus signals and send to PLC bridge

        Returns the complete Modbus Connection document structure with nested signals
        """
        try:
            # Get enabled Modbus Connections with all fields
            connections = frappe.get_all(
                "Modbus Connection",
                filters={"enabled": 1},
                fields=["name", "device_name",
                        "device_type", "host", "port", "enabled"]
            )

            # Initialize connections list with signals
            connection_data = []

            # Get signals for each connection
            for conn in connections:
                # Get basic signal information
                conn_signals = frappe.get_all(
                    "Modbus Signal",
                    filters={"parent": conn.name},
                    fields=["name", "signal_name",
                            "signal_type", "modbus_address"]
                )

                # Process each signal
                processed_signals = []
                for signal in conn_signals:
                    try:
                        # Get the full document to access methods and virtual fields
                        signal_doc = frappe.get_doc(
                            "Modbus Signal", signal["name"])

                        # Use the document's read_signal method to get the current value
                        try:
                            value = signal_doc.read_signal()
                            signal["value"] = value
                        except Exception as e:
                            logger.warning(
                                f"⚠️ Error reading signal {signal['signal_name']}: {str(e)}")
                            # Fallback to default values based on signal type
                            signal["value"] = False if "Digital" in signal["signal_type"] else 0

                        # Add the PLC address virtual field
                        signal["plc_address"] = signal_doc.get_plc_address()

                    except Exception as e:
                        logger.error(
                            f"❌ Error processing signal {signal['name']}: {str(e)}")
                        # Set default values
                        signal["value"] = False if "Digital" in signal["signal_type"] else 0
                        signal["plc_address"] = None

                    processed_signals.append(signal)

                # Add signals to the connection
                conn_data = conn.copy()
                conn_data["signals"] = processed_signals
                connection_data.append(conn_data)

            # Also create a flat list of signals for backward compatibility
            flat_signals = []
            for conn in connection_data:
                flat_signals.extend(conn["signals"])

            # Send to PLC bridge - both the flat list for backward compatibility
            # and the structured connections data
            self.redis.rpush("plc:signals", json.dumps(flat_signals))
            self.redis.rpush("plc:connections", json.dumps(connection_data))

            logger.info(
                f"✅ Sent {len(flat_signals)} signals from {len(connection_data)} connections to PLC bridge")
            return connection_data

        except Exception as e:
            logger.error(f"❌ Error getting signals: {str(e)}")
            return []

    def write_signal(self, signal_name: str, value: Union[bool, int, float]) -> bool:
        """Write a signal value to the PLC"""
        try:
            # Get signal document
            if not frappe.db.exists("Modbus Signal", signal_name):
                logger.warning(f"⚠️ Signal {signal_name} not found")
                return False

            signal = frappe.get_doc("Modbus Signal", signal_name)

            # Check if writable
            if not ("Output" in signal.signal_type or "Register" in signal.signal_type):
                logger.warning(
                    f"⚠️ Cannot write to read-only signal: {signal_name}")
                return False

            # Prepare command
            command = {
                "command": "write_signal",
                "signal": signal_name,
                "value": value
            }

            # Send to PLC bridge
            self.redis.publish("plc:command", json.dumps(command))
            
            # Trigger an immediate check for updates
            # This ensures we quickly process any signal changes that result from this command
            self.trigger_immediate_check()
            
            # Create a direct feedback loop by publishing an immediate update to the frontend
            # This ensures the UI reflects the change even if the real-time update is missed
            try:
                # Publish to Frappe real-time immediately with the expected new state
                # This provides immediate feedback while we wait for the actual PLC confirmation
                logger.info(f"📤 Publishing immediate signal update to Frappe realtime: {signal_name} = {value}")
                frappe.publish_realtime(
                    event='modbus_signal_update',
                    message={
                        'signal': signal_name,
                        'value': value,
                        'timestamp': time.time(),
                        'source': 'write_request' # Mark this as a write request update
                    }
                )
                
                # Schedule a verification check after a short delay to confirm the actual PLC state
                frappe.enqueue(
                    'epibus.utils.plc_redis_client.verify_signal_state',
                    signal_name=signal_name,
                    expected_value=value,
                    queue='short',
                    timeout=30,
                    enqueue_after=2  # Check after 2 seconds to allow PLC to process
                )
                
            except Exception as pub_error:
                logger.warning(f"⚠️ Error publishing immediate update: {str(pub_error)}")
                # Continue even if this fails - the regular update mechanism will still work

            logger.info(f"✏️ Requested write to {signal_name}: {value}")
            return True

        except Exception as e:
            logger.error(f"❌ Error writing signal: {str(e)}")
            return False

    def handle_signal_update(self, message):
        """Handle a signal update from the PLC bridge"""
        try:
            data = json.loads(message)
            signal_name = data.get("name")
            value = data.get("value")

            if not signal_name or value is None:
                logger.warning(f"⚠️ Invalid signal update: {message}")
                return

            # Get signal document
            if not frappe.db.exists("Modbus Signal", signal_name):
                logger.warning(f"⚠️ Signal {signal_name} not found")
                return

            signal = frappe.get_doc("Modbus Signal", signal_name)

            # Log the update
            frappe.get_doc({
                "doctype": "Modbus Event",
                "event_type": "Signal Update",
                "connection": signal.parent,
                "signal": signal_name,
                "value": str(value)
            }).insert(ignore_permissions=True)

            # Find and process actions triggered by this signal
            self._process_signal_actions(signal_name, value)

            # Broadcast to Frappe real-time
            logger.info(
                f"📤 Publishing signal update to Frappe realtime: {signal_name} = {value}")
            frappe.publish_realtime(
                event='modbus_signal_update',
                message={
                    'signal': signal_name,
                    'signal_name': signal.signal_name,
                    'value': value,
                    'timestamp': data.get("timestamp")
                }
            )
            logger.info(f"✅ Published signal update to Frappe realtime")

        except Exception as e:
            logger.error(f"❌ Error handling signal update: {str(e)}")

    def handle_command(self, message):
        """Handle a command from the PLC bridge"""
        try:
            data = json.loads(message)
            command = data.get("command")

            logger.info(f"📥 Received command: {command}")

            if command == "get_signals":
                # Get signals and send them to the PLC bridge
                self.get_signals()
            elif command == "reload_signals":
                # Reload signals from the database
                self.get_signals()
            elif command == "status":
                # Send status update (not implemented yet)
                pass
            elif command == "write_signal":
                # Handle write signal command
                signal_name = data.get("signal")
                value = data.get("value")
                
                if signal_name and value is not None:
                    logger.info(f"📥 Processing write signal command: {signal_name} = {value}")
                    # Get the signal document
                    if frappe.db.exists("Modbus Signal", signal_name):
                        signal = frappe.get_doc("Modbus Signal", signal_name)
                        
                        # Publish the update to Frappe real-time
                        frappe.publish_realtime(
                            event='modbus_signal_update',
                            message={
                                'signal': signal_name,
                                'value': value,
                                'timestamp': time.time(),
                                'source': 'plc_bridge_write'
                            }
                        )
                        logger.info(f"✅ Published write signal update to Frappe realtime: {signal_name} = {value}")
                    else:
                        logger.warning(f"⚠️ Signal {signal_name} not found for write command")
                else:
                    logger.warning(f"⚠️ Invalid write signal command: {data}")
            else:
                logger.warning(f"⚠️ Unknown command: {command}")

        except Exception as e:
            logger.error(f"❌ Error handling command: {str(e)}")

    def _process_signal_actions(self, signal_name, value):
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
                fields=["name", "signal_condition",
                        "signal_value", "server_script"]
            )

            logger.info(
                f"Found {len(actions)} potential actions for signal {signal_name}")

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
                            logger.warning(
                                f"⚠️ Invalid value comparison: {value} == {action.signal_value}")
                            # Fall back to string comparison
                            condition_met = str(value) == action.signal_value
                            condition_desc = f"string equals {action.signal_value}"

                    elif action.signal_condition == "Greater Than":
                        try:
                            target_value = float(action.signal_value)
                            condition_met = float(value) > target_value
                            condition_desc = f"greater than {target_value}"
                        except (ValueError, TypeError):
                            logger.error(
                                f"❌ Invalid comparison for non-numeric value: {value} > {action.signal_value}")

                    elif action.signal_condition == "Less Than":
                        try:
                            target_value = float(action.signal_value)
                            condition_met = float(value) < target_value
                            condition_desc = f"less than {target_value}"
                        except (ValueError, TypeError):
                            logger.error(
                                f"❌ Invalid comparison for non-numeric value: {value} < {action.signal_value}")

                    # Execute action if condition is met
                    if condition_met:
                        logger.info(
                            f"✅ Condition met for action {action.name}: {condition_desc}")

                        # Queue action execution with minimal delay
                        frappe.enqueue(
                            'epibus.utils.plc_redis_client.execute_action',
                            action_name=action.name,
                            signal_name=signal_name,
                            value=value,
                            condition_desc=condition_desc,
                            queue='short',
                            timeout=30
                        )
                    else:
                        logger.debug(
                            f"⏭️ Condition not met for action {action.name}: {condition_desc}")

                except Exception as e:
                    logger.error(
                        f"❌ Error processing action {action.name}: {str(e)}")

        except Exception as e:
            logger.error(f"❌ Error processing signal actions: {str(e)}")
            logger.error(f"❌ Error processing signal actions: {str(e)}")

# Module level functions for background workers


# We'll use a different approach without a persistent pubsub worker

def verify_signal_state(signal_name, expected_value, max_retries=3):
    """
    Verify that a signal has been updated to the expected value in the PLC
    
    This function is called after a write operation to confirm the actual state
    of the PLC and ensure the frontend is updated accordingly.
    
    Args:
        signal_name (str): The name of the signal to verify
        expected_value: The expected value of the signal
        max_retries (int): Maximum number of retries if verification fails
    """
    try:
        logger = get_logger(__name__)
        logger.info(f"🔍 Verifying signal state: {signal_name} = {expected_value}")
        
        # Get the signal document
        if not frappe.db.exists("Modbus Signal", signal_name):
            logger.warning(f"⚠️ Signal {signal_name} not found for verification")
            return
            
        signal = frappe.get_doc("Modbus Signal", signal_name)
        
        # Read the current value directly from the PLC
        try:
            actual_value = signal.read_signal()
            logger.info(f"📊 Actual PLC value for {signal_name}: {actual_value}")
            
            # Check if the value matches the expected value
            if actual_value == expected_value:
                logger.info(f"✅ Signal {signal_name} verified: {actual_value} matches expected {expected_value}")
                
                # Publish the confirmed state to ensure frontend is updated
                frappe.publish_realtime(
                    event='modbus_signal_update',
                    message={
                        'signal': signal_name,
                        'value': actual_value,
                        'timestamp': time.time(),
                        'source': 'verification' # Mark this as a verification update
                    }
                )
            else:
                logger.warning(f"⚠️ Signal {signal_name} verification failed: expected {expected_value}, got {actual_value}")
                
                # If the actual value doesn't match expected, publish the actual value
                # This ensures the frontend shows the true PLC state
                frappe.publish_realtime(
                    event='modbus_signal_update',
                    message={
                        'signal': signal_name,
                        'value': actual_value,
                        'timestamp': time.time(),
                        'source': 'verification_mismatch' # Mark this as a verification mismatch
                    }
                )
                
                # If we have retries left, try writing the value again
                if max_retries > 0:
                    logger.info(f"🔄 Retrying write operation for {signal_name} (retries left: {max_retries})")
                    client = PLCRedisClient.get_instance()
                    client.write_signal(signal_name, expected_value)
                    
                    # Schedule another verification with one less retry
                    frappe.enqueue(
                        'epibus.utils.plc_redis_client.verify_signal_state',
                        signal_name=signal_name,
                        expected_value=expected_value,
                        max_retries=max_retries-1,
                        queue='short',
                        timeout=30,
                        enqueue_after=2
                    )
        except Exception as read_error:
            logger.error(f"❌ Error reading signal for verification: {str(read_error)}")
            
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"❌ Error in signal verification: {str(e)}")

def listen_for_updates(timeout=10, enqueue_after=None):
    """
    Listen for updates from the PLC bridge for a limited time
    
    This function has been disabled as the Redis PLC client has been replaced by the dedicated PLC worker.
    """
    logger.info("⚠️ Redis PLC client listen_for_updates has been disabled - using dedicated PLC worker instead")
    return


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
        logger.info(
            f"🔄 Executing action {action_name} for signal {signal_name} = {value}")
        if condition_desc:
            logger.info(f"Trigger condition: {condition_desc}")

        # Execute the script
        result = None
        if action_doc.server_script:
            script_doc = frappe.get_doc(
                "Server Script", action_doc.server_script)
            result = script_doc.execute_method()

            # Log the execution
            frappe.get_doc({
                "doctype": "Modbus Event",
                "event_type": "Action Execution",
                "connection": connection_doc.name,
                "signal": signal_name,
                "action": action_name,
                "new_value": str(value),
                "status": "Success"
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
                "stack_trace": frappe.get_traceback()
            }).insert(ignore_permissions=True)
        except Exception as log_error:
            logger.error(f"❌ Error logging action failure: {str(log_error)}")

        frappe.log_error(
            f"Error executing Modbus Action {action_name}: {str(e)}")
        return {"success": False, "error": str(e)}
