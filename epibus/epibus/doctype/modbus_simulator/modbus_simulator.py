# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.doctype.modbus_simulator.exceptions import (
    SimulatorException,
    ValidationException,
)
from epibus.epibus.doctype.modbus_simulator.modbus_status_manager import StatusManager
from epibus.epibus.doctype.modbus_simulator.modbus_datastore import DatastoreManager
from epibus.epibus.doctype.modbus_simulator.modbus_server import ModbusServer
from epibus.epibus.doctype.modbus_simulator.modbus_signal_handler import SignalHandler
from epibus.epibus.doctype.modbus_simulator.modbus_script_runner import ScriptRunner

logger = get_logger(__name__)


class ModbusSimulator(Document):
    """Modbus TCP Simulator Document Type

    Provides a configurable Modbus TCP server that can simulate
    various industrial devices with customizable behavior.
    """

    def __init__(self, *args, **kwargs):
        """Initialize simulator components"""
        super().__init__(*args, **kwargs)

        # Initialize managers
        self.status = StatusManager(self)
        self.datastore = DatastoreManager(self)
        self.server = ModbusServer(self)
        self.signals = SignalHandler(self, self.datastore)
        self.script = ScriptRunner(self, self.signals)

    def validate(self):
        """Validate simulator configuration

        Raises:
            ValidationException: If validation fails
        """
        try:
            # Skip validation during status updates
            if (
                hasattr(self.status, "_update_in_progress")
                and self.status._update_in_progress
            ):
                return

            # Validate port range
            if not (1 <= self.server_port <= 65535):
                raise ValidationException("Port must be between 1 and 65535")

            # Validate timeout settings
            if not self.response_timeout or self.response_timeout < 1:
                self.response_timeout = 5
                if self.debug_mode:
                    logger.debug(
                        f"Setting default response timeout to {self.response_timeout}"
                    )

            # Validate reconnect delay
            if not self.reconnect_delay or self.reconnect_delay < 1:
                self.reconnect_delay = 5

            # Prevent changes while running
            if (
                self.has_value_changed("server_port")
                and self.server_status == "Running"
            ):
                raise ValidationException("Cannot change port while server is running")

            if (
                self.has_value_changed("enabled")
                and not self.enabled
                and self.server_status == "Running"
            ):
                raise ValidationException("Stop the server before disabling")

        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            raise ValidationException(f"Validation failed: {str(e)}")

    def on_update(self):
        """Handle document updates"""
        try:
            if (
                hasattr(self.status, "_update_in_progress")
                and self.status._update_in_progress
            ):
                return

            if self.enabled and self.auto_start and self.server_status == "Stopped":
                self.start_simulator()
            elif not self.enabled and self.server_status == "Running":
                self.stop_simulator()

        except Exception as e:
            logger.error(f"Update failed: {str(e)}")
            self.status.error(str(e))

    def after_insert(self):
        """Handle initial document creation"""
        if self.enabled and self.auto_start:
            self.start_simulator()

    def on_trash(self):
        """Clean up before deletion"""
        if self.server_status == "Running":
            self.stop_simulator()

    @frappe.whitelist()
    def start_simulator(self):
        """Start the Modbus TCP simulator

        Returns:
            dict: Success status and any error message
        """
        logger.info(f"Start simulator request received for {self.simulator_name}")

        try:
            # Update status
            self.status.update("Starting")

            # Initialize datastore
            context = self.datastore.initialize()

            # Start server
            self.server.start(context)

            # Start script if configured
            self.script.start()

            # Update final status
            self.status.update("Running")

            logger.info(f"Successfully started simulator {self.simulator_name}")
            return {"success": True}

        except Exception as e:
            error_msg = f"Failed to start simulator: {str(e)}"
            logger.error(error_msg)
            self.cleanup()
            self.status.error(error_msg)
            return {"success": False, "error": error_msg}

    @frappe.whitelist()
    def stop_simulator(self):
        """Stop the Modbus TCP simulator

        Returns:
            dict: Success status and any error message
        """
        logger.info(f"Stop simulator request received for {self.simulator_name}")

        try:
            # Update status
            self.status.update("Stopping")

            # Stop components
            self.cleanup()

            # Update final status
            self.status.update("Stopped")

            logger.info(f"Successfully stopped simulator {self.simulator_name}")
            return {"success": True}

        except Exception as e:
            error_msg = f"Failed to stop simulator: {str(e)}"
            logger.error(error_msg)
            self.status.error(error_msg)
            return {"success": False, "error": error_msg}

    @frappe.whitelist()
    def test_signals(self):
        """Test all configured signals

        Returns:
            dict: Test results for each signal
        """
        try:
            if not self.server.is_ready():
                raise SimulatorException("Server not ready for testing")

            results = self.signals.test_signals()
            return {"success": True, "results": results}

        except Exception as e:
            error_msg = f"Signal test failed: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def cleanup(self):
        """Clean up all simulator resources"""
        try:
            # Stop script first
            self.script.stop()

            # Stop server
            self.server.stop()

            # Clean up datastore
            self.datastore.cleanup()

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise SimulatorException(f"Cleanup failed: {str(e)}")
