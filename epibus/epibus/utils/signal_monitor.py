# epibus/epibus/utils/signal_monitor.py
from epibus.epibus.doctype.modbus_connection.modbus_connection import ModbusConnection
import frappe
from frappe.realtime import publish_realtime
from frappe.utils import now
from epibus.epibus.doctype.modbus_signal.modbus_signal import ModbusSignal
from epibus.epibus.doctype.modbus_action.modbus_action import ModbusAction
from epibus.epibus.doctype.modbus_connection.modbus_connection import ModbusConnection
from epibus.epibus.utils.epinomy_logger import get_logger
from typing import Dict, Any, Optional, cast

logger = get_logger(__name__)


class SignalMonitor:
    """Monitors Modbus signals and publishes changes via Frappe's realtime"""

    _instance: Optional['SignalMonitor'] = None
    active_signals: Dict[str, Any] = {}  # {signal_name: last_value}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _start_monitoring_impl(self, signal_name: str) -> Dict[str, Any]:
        """Internal implementation of start monitoring

        Args:
            signal_name: Name of Modbus Signal document

        Returns:
            dict: Status of monitoring request
        """
        try:
            if signal_name in self.active_signals:
                return {
                    "success": True,
                    "message": f"Already monitoring {signal_name}"
                }

            signal = cast(ModbusSignal, frappe.get_doc(
                "Modbus Signal", signal_name))
            device = cast(ModbusConnection, frappe.get_doc(
                "Modbus Connection", signal.parent))

            if not device.enabled:  # type: ignore
                return {
                    "success": False,
                    "message": f"Device {device.name} is disabled"
                }

            # Store initial value
            value = device.read_signal(signal)  # type: ignore
            self.active_signals[signal_name] = value

            logger.info(f"Started monitoring signal {signal_name}")
            return {
                "success": True,
                "message": f"Started monitoring {signal_name}",
                "initial_value": value
            }

        except Exception as e:
            logger.error(
                f"Error starting monitoring for {signal_name}: {str(e)}")
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

        for signal_name, last_value in list(self.active_signals.items()):
            try:
                signal = cast(ModbusSignal, frappe.get_doc(
                    "Modbus Signal", signal_name))
                device = cast(ModbusConnection, frappe.get_doc(
                    "Modbus Connection", signal.parent))

                if not device.enabled:  # type: ignore
                    logger.warning(
                        f"Device {device.name} disabled - stopping monitoring of {signal_name}")
                    del self.active_signals[signal_name]
                    continue

                current_value = device.read_signal(signal)  # type: ignore

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
                    publish_realtime('modbus_signal_update', update_data)
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
                            action_doc.execute_script()  # type: ignore
                        except Exception as e:
                            logger.error(
                                f"Error executing action {action.name}: {str(e)}")

            except frappe.DoesNotExistError:
                logger.warning(
                    f"Signal {signal_name} no longer exists - removing from monitoring")
                del self.active_signals[signal_name]
            except Exception as e:
                logger.error(f"Error checking signal {signal_name}: {str(e)}")


# Create singleton instance
_signal_monitor = SignalMonitor()


@frappe.whitelist(allow_guest=False, methods=['POST'])
def start_monitoring(signal_name: str) -> Dict[str, Any]:
    """Start monitoring a signal. This is the public API endpoint.

    Args:
        signal_name: Name of Modbus Signal document

    Returns:
        dict: Status of monitoring request
    """
    return _signal_monitor._start_monitoring_impl(signal_name)


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
                "frequency": "All",
                "title": job_name
            })
            job.insert()
            logger.info(f"Created scheduler job: {job_name}")
    except Exception as e:
        logger.error(f"Error setting up scheduler job: {str(e)}")
