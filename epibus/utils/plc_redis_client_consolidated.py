import json
import redis
import frappe
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
        try:
            # Subscribe to both signal updates and commands
            self.pubsub.subscribe("plc:signal_update", "plc:command")

            # Start background worker
            frappe.enqueue(
                'epibus.utils.plc_redis_client_consolidated.pubsub_worker',
                queue='long',
                timeout=None
            )

            logger.info("🔄 Started Redis pubsub listener")

        except Exception as e:
            logger.error(f"❌ Error starting Redis pubsub listener: {str(e)}")

    def get_signals(self) -> List[Dict[str, Any]]:
        """Get all Modbus signals and send to PLC bridge"""
        try:
            # Get enabled Modbus Connections
            connections = frappe.get_all(
                "Modbus Connection",
                filters={"enabled": 1},
                fields=["name"]
            )

            # Initialize signals list
            signals = []

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
                                f"⚠️ Error reading signal {signal['name']}: {str(e)}")
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

                # Add to signals list
                signals.extend(conn_signals)

            # Send to PLC bridge
            self.redis.rpush("plc:signals", json.dumps(signals))

            logger.info(f"✅ Sent {len(signals)} signals to PLC bridge")
            return signals

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

            # Log event locally as well
            frappe.get_doc({
                "doctype": "Modbus Event",
                "event_type": "Signal Write",
                "signal": signal_name,
                "value": str(value)
            }).insert(ignore_permissions=True)

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

            # Update signal value in database
            if isinstance(value, bool):
                signal.db_set('digital_value', value)
            else:
                signal.db_set('float_value', float(value))

            # Log the update
            frappe.get_doc({
                "doctype": "Modbus Event",
                "event_type": "Signal Update",
                "signal": signal_name,
                "value": str(value)
            }).insert(ignore_permissions=True)

            # Find and process actions triggered by this signal
            self._process_signal_actions(signal_name, value)

            # Broadcast to Frappe real-time
            frappe.publish_realtime(
                event='modbus_signal_update',
                message={
                    'signal': signal_name,
                    'value': value,
                    'timestamp': data.get("timestamp")
                }
            )

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
            else:
                logger.warning(f"⚠️ Unknown command: {command}")

        except Exception as e:
            logger.error(f"❌ Error handling command: {str(e)}")

    def _process_signal_actions(self, signal_name, value):
        """Process actions triggered by a signal update"""
        try:
            # Find applicable actions
            actions = frappe.get_all(
                "Modbus Action",
                filters={
                    "signal": signal_name,
                    "enabled": 1,
                    "trigger_type": "Signal Change"
                },
                fields=["name", "server_script"]
            )

            # Process each action
            for action in actions:
                try:
                    # Queue action execution with minimal delay
                    frappe.enqueue(
                        'epibus.utils.plc_redis_client_consolidated.execute_action',
                        action_name=action.name,
                        signal_name=signal_name,
                        value=value,
                        queue='short',
                        timeout=30
                    )
                except Exception as e:
                    logger.error(
                        f"❌ Error enqueueing action {action.name}: {str(e)}")

        except Exception as e:
            logger.error(f"❌ Error processing signal actions: {str(e)}")

# Module level functions for background workers


def pubsub_worker():
    """Background worker for Redis pubsub"""
    client = PLCRedisClient.get_instance()

    logger.info("🔄 Starting Redis pubsub worker")

    try:
        # Process messages
        while True:
            message = client.pubsub.get_message()
            if message and message["type"] == "message":
                channel = message["channel"]

                if channel == b"plc:signal_update":
                    client.handle_signal_update(message["data"])
                elif channel == b"plc:command":
                    client.handle_command(message["data"])

            frappe.db.commit()
            frappe.local.db.commit()  # Ensure DB changes are committed

    except Exception as e:
        logger.error(f"❌ Error in Redis pubsub worker: {str(e)}")

        # Re-enqueue the worker to restart it
        frappe.enqueue(
            'epibus.utils.plc_redis_client_consolidated.pubsub_worker',
            queue='long',
            timeout=None
        )


def execute_action(action_name, signal_name, value):
    """Execute a Modbus Action"""
    try:
        # Get the action document
        action_doc = frappe.get_doc("Modbus Action", action_name)

        # Get the signal document
        signal_doc = frappe.get_doc("Modbus Signal", signal_name)

        # Get the parent device
        device_doc = frappe.get_doc("Modbus Connection", signal_doc.parent)

        # Setup context for the script
        frappe.flags.modbus_context = {
            "device": device_doc,
            "signal": signal_doc,
            "value": value
        }

        # Execute the script
        result = None
        if action_doc.server_script:
            script_doc = frappe.get_doc(
                "Server Script", action_doc.server_script)
            result = script_doc.execute_method()

        # Clear context
        frappe.flags.modbus_context = None

        logger.info(f"✅ Executed action {action_name}")
        return result

    except Exception as e:
        logger.error(f"❌ Error executing action {action_name}: {str(e)}")
        frappe.log_error(
            f"Error executing Modbus Action {action_name}: {str(e)}")
        return {"success": False, "error": str(e)}
