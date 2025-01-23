# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt

import threading
import socket
import time
from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.doctype.modbus_simulator.exceptions import ServerException

logger = get_logger(__name__)


class ModbusServer:
    """Manages Modbus TCP server lifecycle and threading"""

    def __init__(self, simulator_doc):
        """Initialize server manager

        Args:
            simulator_doc: Parent ModbusSimulator document
        """
        self.doc = simulator_doc
        self.server = None
        self.server_thread = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()

    def start(self, context):
        """Start the Modbus TCP server

        Args:
            context: ModbusServerContext from datastore

        Raises:
            ServerException: If server fails to start
        """
        try:
            # Check if port is available
            self._check_port_available()

            # Clear control flags
            self._stop_event.clear()
            self._ready_event.clear()

            # Start server thread
            self.server_thread = threading.Thread(
                target=self._run_server, args=(context,)
            )
            self.server_thread.daemon = True

            logger.debug(f"Starting server thread on port {self.doc.server_port}")
            self.server_thread.start()

            # Wait for server to be ready
            if not self._ready_event.wait(timeout=10.0):
                raise ServerException("Server failed to start within timeout")

            logger.info(f"Server started successfully on port {self.doc.server_port}")

        except Exception as e:
            error_msg = f"Failed to start server: {str(e)}"
            logger.error(error_msg)
            self.cleanup()
            raise ServerException(error_msg)

    def stop(self):
        """Stop the server and cleanup resources

        Raises:
            ServerException: If cleanup fails
        """
        try:
            logger.debug("Initiating server shutdown")
            self._stop_event.set()
            self._ready_event.clear()
            self.cleanup()
            logger.info("Server stopped successfully")

        except Exception as e:
            error_msg = f"Error stopping server: {str(e)}"
            logger.error(error_msg)
            raise ServerException(error_msg)

    def cleanup(self):
        """Clean up server resources"""
        try:
            if self.server:
                try:
                    logger.debug("Shutting down server socket...")
                    if hasattr(self.server, "server_close"):
                        self.server.server_close()
                    if hasattr(self.server, "socket"):
                        self.server.socket.shutdown(socket.SHUT_RDWR)
                        self.server.socket.close()
                except Exception as e:
                    logger.error(f"Error during socket cleanup: {str(e)}")
                finally:
                    self.server = None

            if self.server_thread and self.server_thread.is_alive():
                logger.debug("Waiting for server thread to exit...")
                self.server_thread.join(timeout=5.0)
                if self.server_thread.is_alive():
                    logger.warning("Server thread did not exit cleanly")

            self.server_thread = None

        except Exception as e:
            error_msg = f"Error during server cleanup: {str(e)}"
            logger.error(error_msg)
            raise ServerException(error_msg)

    def is_ready(self):
        """Check if server is ready for operations

        Returns:
            bool: True if server is running and ready
        """
        return (
            self.server is not None
            and hasattr(self.server, "socket")
            and self.server.socket is not None
            and self._ready_event.is_set()
            and not self._stop_event.is_set()
        )

    def _run_server(self, context):
        """Run the Modbus TCP server (called in thread)

        Args:
            context: ModbusServerContext from datastore
        """
        try:
            if self.doc.debug_mode:
                logger.debug(
                    f"Starting Modbus server on 127.0.0.1:{self.doc.server_port}"
                )

            # Create identity information
            identity = ModbusDeviceIdentification(
                info_name={
                    "VendorName": "EpiBus Simulator",
                    "ProductCode": "MBSIM",
                    "ModelName": self.doc.simulator_name,
                    "MajorMinorRevision": "1.0",
                }
            )

            # Start server
            self.server = StartTcpServer(
                context=context,
                address=("127.0.0.1", self.doc.server_port),
                identity=identity,
            )

            # Verify binding
            if not hasattr(self.server, "socket") or not self.server.socket:
                raise ServerException("Server failed to bind to socket")

            if self.doc.debug_mode:
                logger.debug("Server bound successfully")

            # Signal ready
            self._ready_event.set()

            # Main server loop
            while not self._stop_event.is_set():
                if not self.is_ready():
                    logger.error("Server lost socket binding")
                    break
                time.sleep(0.1)

        except Exception as e:
            error_msg = f"Server error: {str(e)}"
            logger.error(error_msg)
            raise ServerException(error_msg)

        finally:
            self._ready_event.clear()

    def _check_port_available(self):
        """Check if server port is available

        Raises:
            ServerException: If port is in use
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(("127.0.0.1", self.doc.server_port))
            if result == 0:
                raise ServerException(f"Port {self.doc.server_port} is already in use")
        finally:
            sock.close()
