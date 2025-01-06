# epibus/epibus/utils/signal_monitor.py
import frappe
from frappe.realtime import publish_realtime
from epibus.epibus.utils.epinomy_logger import get_logger
from typing import Dict, Any, Optional

logger = get_logger(__name__)

class SignalMonitor:
    """Monitors Modbus signals and publishes changes via Frappe's realtime"""
    
    _instance: Optional['SignalMonitor'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.active_signals = {}  # {signal_name: last_value}
        return cls._instance
        
    @frappe.whitelist()
    def start_monitoring(self, signal_name: str) -> Dict[str, Any]:
        """Start monitoring a signal
        
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
                
            signal = frappe.get_doc("Modbus Signal", signal_name)
            device = frappe.get_doc("Modbus Device", signal.parent)
            
            if not device.enabled:
                return {
                    "success": False,
                    "message": f"Device {device.name} is disabled"
                }
                
            # Store initial value
            value = device.read_signal(signal)
            self.active_signals[signal_name] = value
            
            logger.info(f"Started monitoring signal {signal_name}")
            return {
                "success": True,
                "message": f"Started monitoring {signal_name}",
                "initial_value": value
            }
            
        except Exception as e:
            logger.error(f"Error starting monitoring for {signal_name}: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }
            
    def check_signals(self) -> None:
        """Poll active signals and publish changes. Called by scheduler."""
        if not self.active_signals:
            return
            
        for signal_name, last_value in list(self.active_signals.items()):
            try:
                signal = frappe.get_doc("Modbus Signal", signal_name)
                device = frappe.get_doc("Modbus Device", signal.parent)
                
                if not device.enabled:
                    logger.warning(f"Device {device.name} disabled - stopping monitoring of {signal_name}")
                    del self.active_signals[signal_name]
                    continue
                
                current_value = device.read_signal(signal)
                
                if current_value != last_value:
                    # Value changed - update cache and publish
                    self.active_signals[signal_name] = current_value
                    
                    # Publish realtime update
                    update_data = {
                        'signal': signal_name,
                        'value': current_value,
                        'timestamp': frappe.utils.now()
                    }
                    publish_realtime('modbus_signal_update', update_data)
                    logger.debug(f"Published update for {signal_name}: {current_value}")
                    
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
                            action_doc = frappe.get_doc("Modbus Action", action.name)
                            action_doc.execute_script()
                        except Exception as e:
                            logger.error(f"Error executing action {action.name}: {str(e)}")
                            
            except frappe.DoesNotExistError:
                logger.warning(f"Signal {signal_name} no longer exists - removing from monitoring")
                del self.active_signals[signal_name]
            except Exception as e:
                logger.error(f"Error checking signal {signal_name}: {str(e)}")

# Create singleton instance
signal_monitor = SignalMonitor()

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

def check_signals():
    """Wrapper for scheduler to call singleton instance method"""
    signal_monitor.check_signals()