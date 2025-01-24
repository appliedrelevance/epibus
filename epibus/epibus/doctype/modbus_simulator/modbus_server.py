# Copyright (c) 2024, Applied Relevance, LLC and contributors
# For license information, please see license.txt

import socket
import time
import frappe
import asyncio
from pymodbus.server import StartAsyncTcpServer
from pymodbus.device import ModbusDeviceIdentification
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.doctype.modbus_simulator.exceptions import ServerException

logger = get_logger(__name__)


class ModbusServer:
    """Manages Modbus TCP server and script execution"""

    def __init__(self, simulator_doc):
        """Initialize server manager"""
        self.doc = simulator_doc
        self._stop_flag_key = f"stop_simulator_{self.doc.name}"
        self._running_key = f"simulator_running_{self.doc.name}"
        self._status_key = f"simulator_script_status_{self.doc.name}"

    def start(self, context):
        """Start the Modbus TCP server and script"""
        try:
            # Check port availability
            self._check_port_available()

            # Clear control flags
            self._clear_cache_flags()

            # Create identity information
            identity = ModbusDeviceIdentification(
                info={  # Use info instead of info_name
                    0x00: "EpiBus Simulator",  # VendorName
                    0x01: "MBSIM",  # ProductCode
                    0x02: "1.0",  # MajorMinorRevision
                    0x05: self.doc.simulator_name,  # ModelName
                }
            )

            # Start server and script in background job
            job = frappe.enqueue(
                "epibus.epibus.doctype.modbus_simulator.modbus_server._run_server_and_script",
                simulator_name=self.doc.name,
                context=context,
                identity=identity,
                port=self.doc.server_port,
                queue="long",
                timeout=None,
            )

            logger.info(f"Server job started with ID: {job.id}")
            return job

        except Exception as e:
            error_msg = f"Failed to start server: {str(e)}"
            logger.error(error_msg)
            raise ServerException(error_msg)

    def stop(self):
        """Stop the server and script"""
        try:
            # Set stop flag
            frappe.cache().set(self._stop_flag_key, 1)

            # Wait briefly for cleanup
            time.sleep(2)

            self._clear_cache_flags()
            logger.info("Server stopped")

        except Exception as e:
            error_msg = f"Failed to stop server: {str(e)}"
            logger.error(error_msg)
            raise ServerException(error_msg)

    def is_ready(self):
        """Check if server is ready"""
        return bool(frappe.cache().get(self._running_key))

    def _check_port_available(self):
        """Check if server port is available"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(("127.0.0.1", self.doc.server_port))
            if result == 0:
                raise ServerException(f"Port {self.doc.server_port} is already in use")
        finally:
            sock.close()

    def _clear_cache_flags(self):
        """Clear all cache flags"""
        frappe.cache().delete_key(self._stop_flag_key)
        frappe.cache().delete_key(self._running_key)
        frappe.cache().delete_key(self._status_key)

    def is_running(self):
        """Check if simulator is actually running"""
        try:
            # Check job exists and is running
            jobs = frappe.get_all(
                "Queue Job",
                filters={
                    "queue": "long",
                    "status": "started",
                    "reference_name": self.doc.name,
                },
            )
            if not jobs:
                return False

            # Verify port is bound
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                result = sock.connect_ex(("127.0.0.1", self.doc.server_port))
                return result == 0
            finally:
                sock.close()

        except Exception as e:
            logger.error(f"Status check failed: {str(e)}")
            return False


def _run_server_and_script(simulator_name, context, identity, port):
    """Background job function to run server and script"""
    loop = None
    try:
        doc = frappe.get_doc("Modbus Simulator", simulator_name)
        logger.debug(f"Starting server for {simulator_name} on port {port}")

        frappe.cache().set(f"simulator_running_{simulator_name}", 1)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        server = loop.run_until_complete(
            StartAsyncTcpServer(
                context=context, identity=identity, address=("127.0.0.1", port)
            )
        )

        logger.info(f"Server started on port {port}")

        loop.run_forever()

    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        if "doc" in locals():
            doc.status.error(str(e))
    finally:
        if loop and loop.is_running():
            loop.stop()
            loop.close()
        if frappe.cache():
            frappe.cache().delete_key(f"simulator_running_{simulator_name}")
