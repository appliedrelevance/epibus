# epibus/epibus/utils/signal_monitor.py
from epibus.epibus.doctype.modbus_connection.modbus_connection import ModbusConnection
from epibus.epibus.doctype.modbus_action.modbus_action import ModbusAction
import frappe
from frappe.realtime import publish_realtime
from frappe.utils import now
from epibus.epibus.doctype.modbus_event.modbus_event import ModbusEvent
from epibus.epibus.utils.epinomy_logger import get_logger
from typing import Dict, Any, Optional, cast, TypeVar, Union
from collections import defaultdict

logger = get_logger(__name__)

SignalValue = Union[bool, float, int]


class SignalMonitor:
    """Monitors Modbus signals and publishes changes via Frappe's realtime"""

    _instance: Optional['SignalMonitor'] = None
    active_signals: Dict[str, SignalValue] = {}  # {signal_name: last_value}
    device_signals: Dict[str, list] = defaultdict(
        list)  # {device_name: [signal_names]}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _start_monitoring_impl(self, signal_id: str) -> Dict[str, Any]:
        """Internal implementation of start monitoring

        Args:
            signal_id: The unique identifier of the Modbus Signal document

        Returns:
            dict: Status of monitoring request
        """
        try:
            if signal_id in self.active_signals:
                return {
                    "success": True,
                    "message": f"Already monitoring {signal_id}"
                }

            # Get signal document
            signal_doc = frappe.get_doc("Modbus Signal", signal_id)
            if not signal_doc:
                raise ValueError(f"Signal {signal_id} not found")

            # Get parent device document
            parent_name = str(signal_doc.get("parent"))
            device_doc = cast(ModbusConnection, frappe.get_doc(
                "Modbus Connection", parent_name))
            if not device_doc:
                raise ValueError(f"Device not found for signal {signal_id}")

            if not device_doc.enabled:
                return {
                    "success": False,
                    "message": f"Device {device_doc.name} is disabled"
                }

            # Store initial value
            value = device_doc.read_signal(signal_doc)
            self.active_signals[signal_id] = value

            # Group signals by device for batch reading
            self.device_signals[parent_name].append(signal_id)

            logger.info(f"Started monitoring signal {signal_id}")
            return {
                "success": True,
                "message": f"Started monitoring {signal_id}",
                "initial_value": value
            }

        except Exception as e:
            logger.error(
                f"Error starting monitoring for {signal_id}: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }

    def check_signals(self) -> None:
        """Poll active signals and publish changes. Called by scheduler."""
        logger.info(
            f"Signal checker starting - monitoring {len(self.active_signals)} signals")

        if not self.active_signals:
            logger.debug("No active signals to monitor")
            return

        # Process signals grouped by device to minimize connections
        for device_name, signal_names in self.device_signals.items():
            try:
                device_doc = cast(ModbusConnection, frappe.get_doc(
                    "Modbus Connection", device_name))

                if not device_doc.enabled:
                    logger.warning(
                        f"Device {device_name} disabled - stopping monitoring of all its signals")
                    for signal_name in signal_names:
                        if signal_name in self.active_signals:
                            del self.active_signals[signal_name]
                    del self.device_signals[device_name]
                    continue

                # Get a single client connection for all signals on this device
                client = device_doc.get_client()

                for signal_name in signal_names:
                    try:
                        signal_doc = frappe.get_doc(
                            "Modbus Signal", signal_name)
                        if not signal_doc:
                            raise frappe.DoesNotExistError(
                                f"Signal {signal_name} not found")

                        last_value = self.active_signals.get(signal_name)
                        current_value = device_doc.read_signal(signal_doc)

                        if current_value != last_value:
                            # Value changed - update cache and publish
                            self.active_signals[signal_name] = current_value

                            # Log the value change
                            logger.info(
                                f"Signal {signal_name} value changed: {last_value} -> {current_value}")

                            # Publish realtime update
                            update_data = {
                                'signal': signal_name,
                                'value': current_value,
                                'timestamp': now()
                            }
                            publish_realtime(
                                'modbus_signal_update', update_data)
                            logger.debug(
                                f"Published update for {signal_name}: {current_value}")

                            # Find and execute relevant actions
                            actions = frappe.get_all(
                                "Modbus Action",
                                filters={
                                    "signal": signal_name,
                                    "enabled": 1,
                                    "trigger_type": "API"
                                }
                            )

                            for action in actions:
                                try:
                                    action_doc = cast(ModbusAction, frappe.get_doc(
                                        "Modbus Action", action.name))
                                    action_doc.execute_script()
                                except Exception as e:
                                    logger.error(
                                        f"Error executing action {action.name}: {str(e)}")

                    except frappe.DoesNotExistError:
                        logger.warning(
                            f"Signal {signal_name} no longer exists - removing from monitoring")
                        if signal_name in self.active_signals:
                            del self.active_signals[signal_name]
                        self.device_signals[device_name].remove(signal_name)
                    except Exception as e:
                        logger.error(
                            f"Error checking signal {signal_name}: {str(e)}")

            except Exception as e:
                logger.error(
                    f"Error processing device {device_name}: {str(e)}")

            # Clean up empty device groups
            if not self.device_signals[device_name]:
                del self.device_signals[device_name]


# Create singleton instance
_signal_monitor = SignalMonitor()


@frappe.whitelist(allow_guest=False, methods=['POST'])
def start_monitoring(**kwargs) -> Dict[str, Any]:
    """Start monitoring a signal. This is the public API endpoint.

    Args:
        kwargs: Expected to contain signal_id parameter

    Returns:
        dict: Status of monitoring request
    """
    if 'signal_id' not in kwargs:
        return {
            "success": False,
            "message": "signal_id parameter is required"
        }
    return _signal_monitor._start_monitoring_impl(kwargs['signal_id'])


def check_signals():
    """Wrapper for scheduler to call singleton instance method"""
    _signal_monitor.check_signals()


def setup_scheduler_job():
    """Create or update the scheduler job for signal monitoring"""
    try:
        job_name = "Check Modbus Signals"

        # Check if job exists
        existing_job = frappe.db.exists(
            "Scheduled Job Type",
            {"method": "epibus.epibus.utils.signal_monitor.check_signals"}
        )

        if not existing_job:
            job = frappe.get_doc({
                "doctype": "Scheduled Job Type",
                "method": "epibus.epibus.utils.signal_monitor.check_signals",
                "frequency": "Cron",
                "cron_format": "*/5 * * * *",  # Run every 5 minutes instead of "All"
                "title": job_name
            })
            job.insert()
            logger.info(f"Created scheduler job: {job_name}")
    except Exception as e:
        logger.error(f"Error setting up scheduler job: {str(e)}")


def publish_signal_update(signal_name: str, value: SignalValue) -> None:
    """Publish a signal update to the realtime system and update monitoring cache.

    Args:
        signal_name: Name of the Modbus Signal document
        value: New value to publish
    """
    try:
        # Update monitoring cache
        _signal_monitor.active_signals[signal_name] = value

        # Publish realtime update
        update_data = {
            'signal': signal_name,
            'value': value,
            'timestamp': now()
        }
        publish_realtime('modbus_signal_update', update_data)
        logger.debug(f"Published immediate update for {signal_name}: {value}")

    except Exception as e:
        logger.error(
            f"Error publishing signal update for {signal_name}: {str(e)}")
