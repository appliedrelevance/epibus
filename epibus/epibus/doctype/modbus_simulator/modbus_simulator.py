# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.doctype.modbus_simulator.exceptions import (
    SimulatorException,
    ValidationException,
)
from pymodbus.client import ModbusTcpClient
import socket
from epibus.epibus.doctype.modbus_simulator.modbus_status_manager import StatusManager
from epibus.epibus.doctype.modbus_simulator.modbus_datastore import DatastoreManager
from epibus.epibus.doctype.modbus_simulator.modbus_server import ModbusServer
from epibus.epibus.doctype.modbus_simulator.modbus_signal_handler import SignalHandler

logger = get_logger(__name__)


class ModbusSimulator(Document):
    """Modbus TCP Simulator Document Type"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = StatusManager(self)
        self.datastore = DatastoreManager(self)
        self.signals = SignalHandler(self, self.datastore)
        self.server = ModbusServer(self)
        self._job = None

    def validate(self):
        try:
            if (
                hasattr(self.status, "_update_in_progress")
                and self.status._update_in_progress
            ):
                return

            if not (1 <= self.server_port <= 65535):
                raise ValidationException("Port must be between 1 and 65535")

            if not self.response_timeout or self.response_timeout < 1:
                self.response_timeout = 5
                if self.debug_mode:
                    logger.debug(
                        f"Setting default response timeout to {self.response_timeout}"
                    )

            if not self.reconnect_delay or self.reconnect_delay < 1:
                self.reconnect_delay = 5

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
        if self.enabled and self.auto_start:
            self.start_simulator()

    def on_trash(self):
        if self.server_status == "Running":
            self.stop_simulator()

    @frappe.whitelist()
    def start_simulator(self):
        logger.info(f"Start simulator request received for {self.simulator_name}")

        try:
            self.status.update("Starting")
            context = self.datastore.initialize()
            self._job = self.server.start(context)
            self.status.update("Running")
            return {"success": True, "job": self._job.id}

        except Exception as e:
            error_msg = f"Failed to start simulator: {str(e)}"
            logger.error(error_msg)
            self.cleanup()
            self.status.error(error_msg)
            return {"success": False, "error": error_msg}

    @frappe.whitelist()
    def stop_simulator(self):
        logger.info(f"Stop simulator request received for {self.simulator_name}")

        try:
            self.status.update("Stopping")
            self.cleanup()
            self.status.update("Stopped")
            return {"success": True}

        except Exception as e:
            error_msg = f"Failed to stop simulator: {str(e)}"
            logger.error(error_msg)
            self.status.error(error_msg)
            return {"success": False, "error": error_msg}

    @frappe.whitelist()
    def test_signals(self):
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
        try:
            self.server.stop()
            self.datastore.cleanup()
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise SimulatorException(f"Cleanup failed: {str(e)}")


@frappe.whitelist()
def test_connection(simulator_name):
    """Test actual Modbus TCP connection"""

    try:
        # Retrieve simulator document
        doc = frappe.get_doc("Modbus Simulator", simulator_name)

        # Create Modbus TCP client
        client = ModbusTcpClient(
            "127.0.0.1", port=doc.server_port, timeout=doc.response_timeout
        )

        # Attempt to connect
        connection = client.connect()
        if not connection:
            return {
                "success": False,
                "error": "Failed to establish Modbus TCP connection",
            }

        # Attempt a basic read (coil read at address 0)
        try:
            result = client.read_coils(0, 1)
            if result.isError():
                return {"success": False, "error": "Error reading coils"}
        except Exception as e:
            return {"success": False, "error": f"Read error: {str(e)}"}
        finally:
            client.close()

        return {"success": True, "message": "Modbus TCP connection successful"}

    except socket.error as se:
        logger.error(
            f"Socket error during connection test for {simulator_name}: {str(se)}"
        )
        return {"success": False, "error": f"Network error: {str(se)}"}
    except Exception as e:
        logger.error(f"Connection test failed for {simulator_name}: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def verify_simulator_status():
    """Update simulator status based on actual job/server state"""
    simulators = frappe.get_all("Modbus Simulator")

    for sim in simulators:
        doc = frappe.get_doc("Modbus Simulator", sim.name)

        # Check actual status
        is_running = doc.server.is_running()
        current_status = doc.server_status

        # Update if mismatch
        if is_running and current_status != "Running":
            doc.status.update("Running")
        elif not is_running and current_status == "Running":
            doc.status.update("Stopped")
            doc.cleanup()  # Clean up stale resources
