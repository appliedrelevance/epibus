# Copyright (c) 2024, Applied Relevance, LLC and contributors
# For license information, please see license.txt

import socket
import asyncio
import threading
from pymodbus.server import StartAsyncTcpServer
from pymodbus.device import ModbusDeviceIdentification
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.doctype.modbus_simulator.exceptions import ServerException

logger = get_logger(__name__)


async def run_server(context, identity, port):
    # Create task with timeout
    task = asyncio.create_task(
        StartAsyncTcpServer(
            context=context, identity=identity, address=("127.0.0.1", port)
        )
    )
    try:
        result = await asyncio.wait_for(task, timeout=5.0)
        return result
    except asyncio.TimeoutError:
        task.cancel()
        raise ServerException("Server failed to start - timed out")


def run_async_server(context, identity, port, ready_event):
    """Run the async server in a dedicated event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(run_server(context, identity, port))
        ready_event.set()
        loop.run_forever()
    finally:
        loop.close()


class ModbusServer:
    """Manages Modbus TCP server lifecycle and threading."""

    def __init__(self, simulator_doc):
        """Initialize server manager."""
        self.doc = simulator_doc
        self.server = None
        self._ready_event = threading.Event()

    def start(self, context):
        """Start the Modbus TCP server."""
        try:
            # Check port availability
            self._check_port_available()

            # Create identity information
            identity = ModbusDeviceIdentification(
                info_name={
                    "VendorName": "EpiBus Simulator",
                    "ProductCode": "MBSIM",
                    "ModelName": self.doc.simulator_name,
                    "MajorMinorRevision": "1.0",
                }
            )

            # Start server in separate thread
            server_thread = threading.Thread(
                target=run_async_server,
                args=(context, identity, self.doc.server_port, self._ready_event),
                daemon=True,
            )
            server_thread.start()

            # Wait for server to be ready
            if not self._ready_event.wait(timeout=10.0):
                raise ServerException("Server failed to start within timeout")

            logger.info(f"Server started successfully on port {self.doc.server_port}")

        except Exception as e:
            error_msg = f"Failed to start server: {str(e)}"
            logger.error(error_msg)
            raise ServerException(error_msg)

    def stop(self):
        """Stop the server."""
        if self.server:
            self.server.server_close()
            self.server = None
            logger.info("Server stopped")

    def is_ready(self):
        """Check if server is ready."""
        return self._ready_event.is_set()

    def _check_port_available(self):
        """Check if server port is available."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(("127.0.0.1", self.doc.server_port))
            if result == 0:
                raise ServerException(f"Port {self.doc.server_port} is already in use")
        finally:
            sock.close()
