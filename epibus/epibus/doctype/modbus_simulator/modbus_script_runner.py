# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
import time
import threading
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.doctype.modbus_simulator.exceptions import ScriptException

logger = get_logger(__name__)


class ScriptRunner:
    """Manages simulator script execution environment"""

    def __init__(self, simulator_doc, signal_handler):
        """Initialize script runner

        Args:
            simulator_doc: Parent ModbusSimulator document
            signal_handler: SignalHandler instance
        """
        self.doc = simulator_doc
        self.signals = signal_handler
        self._script_thread = None
        self._stop_flag_key = f"stop_simulator_{self.doc.name}"
        self._running_key = f"simulator_running_{self.doc.name}"
        self._status_key = f"simulator_script_status_{self.doc.name}"

    def start(self):
        """Start the simulator script in a new thread

        Raises:
            ScriptException: If script fails to start
        """
        if not self.doc.simulator_script:
            logger.info(f"No script configured for {self.doc.simulator_name}")
            return

        try:
            # Clear control flags
            self._clear_cache_flags()

            # Start script thread
            self._script_thread = threading.Thread(target=self._run_script)
            self._script_thread.daemon = True

            logger.debug(f"Starting script thread for {self.doc.simulator_name}")
            self._script_thread.start()

        except Exception as e:
            error_msg = f"Failed to start script: {str(e)}"
            logger.error(error_msg)
            raise ScriptException(error_msg)

    def stop(self):
        """Stop the running script

        Raises:
            ScriptException: If script fails to stop
        """
        try:
            # Set stop flag
            frappe.cache().set(self._stop_flag_key, 1)

            # Wait for thread to exit
            if self._script_thread and self._script_thread.is_alive():
                logger.debug("Waiting for script thread to exit...")
                self._script_thread.join(timeout=5.0)
                if self._script_thread.is_alive():
                    logger.warning("Script thread did not exit cleanly")

            self._script_thread = None
            self._clear_cache_flags()

        except Exception as e:
            error_msg = f"Failed to stop script: {str(e)}"
            logger.error(error_msg)
            raise ScriptException(error_msg)

    def is_running(self):
        """Check if script is currently running

        Returns:
            bool: True if script is running
        """
        return bool(frappe.cache().get(self._running_key))

    def get_status(self):
        """Get current script status

        Returns:
            str: Current status message
        """
        return frappe.cache().get(self._status_key) or "Not running"

    def _run_script(self):
        """Execute the simulator script

        This provides a controlled environment for script execution
        with access to simulator functionality.
        """
        try:
            frappe.cache().set(self._running_key, 1)
            frappe.cache().set(self._status_key, "Running")

            if self.doc.debug_mode:
                logger.debug(f"Script content:\n{self.doc.simulator_script}")

            # Create script globals
            script_globals = {"simulator": self._create_simulator_api(), "time": time}

            # Execute script to define functions
            exec(self.doc.simulator_script, script_globals)

            # Call run() if defined
            if "run" in script_globals:
                logger.debug("Executing run() function")
                script_globals["run"](script_globals["simulator"])
            else:
                logger.warning("No run() function found in script")

        except Exception as e:
            error_msg = f"Script error: {str(e)}"
            logger.error(error_msg)
            self.doc.error_message = error_msg
            self.doc.db_set("error_message", error_msg)
            frappe.cache().set(self._status_key, f"Error: {str(e)}")

        finally:
            frappe.cache().set(self._running_key, 0)
            self._clear_cache_flags()

    def _create_simulator_api(self):
        """Create API object exposed to simulator scripts

        Returns:
            SimulatorAPI: API object for scripts
        """
        return SimulatorAPI(self)

    def _clear_cache_flags(self):
        """Clear all cache flags used by script"""
        frappe.cache().delete_key(self._stop_flag_key)
        frappe.cache().delete_key(self._running_key)
        frappe.cache().delete_key(self._status_key)


class SimulatorAPI:
    """API exposed to simulator scripts"""

    def __init__(self, runner):
        """Initialize API wrapper

        Args:
            runner: ScriptRunner instance
        """
        self._runner = runner
        self.signals = runner.signals

    def read_signal(self, name):
        """Read signal value

        Args:
            name: Signal name

        Returns:
            bool or float: Signal value
        """
        return self.signals.read_signal(name)

    def write_signal(self, name, value):
        """Write signal value

        Args:
            name: Signal name
            value: Value to write
        """
        self.signals.write_signal(name, value)

    def toggle_signal(self, name):
        """Toggle digital signal

        Args:
            name: Signal name

        Returns:
            bool: New signal value
        """
        return self.signals.toggle_signal(name)

    def sleep(self, seconds):
        """Sleep while checking for stop

        Args:
            seconds: Time to sleep

        Raises:
            InterruptedError: If simulator is stopped
        """
        end_time = time.time() + seconds
        while time.time() < end_time:
            if frappe.cache().get(self._runner._stop_flag_key) == 1:
                raise InterruptedError("Simulator stopped")
            time.sleep(0.1)

    def log_debug(self, message):
        """Log debug message

        Args:
            message: Message to log
        """
        if self._runner.doc.debug_mode:
            logger.debug(f"[{self._runner.doc.simulator_name}] {message}")

    def log_info(self, message):
        """Log info message

        Args:
            message: Message to log
        """
        logger.info(f"[{self._runner.doc.simulator_name}] {message}")

    def log_warning(self, message):
        """Log warning message

        Args:
            message: Message to log
        """
        logger.warning(f"[{self._runner.doc.simulator_name}] {message}")

    def log_error(self, message):
        """Log error message

        Args:
            message: Message to log
        """
        logger.error(f"[{self._runner.doc.simulator_name}] {message}")
        self._runner.doc.db_set("error_message", message)
