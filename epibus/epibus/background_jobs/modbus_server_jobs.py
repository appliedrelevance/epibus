import frappe
import asyncio
from pymodbus.server.async_io import StartAsyncTcpServer
from pymodbus.server import ServerAsyncStop
import logging

# Configure logging with a more detailed format and debug level on root logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def check_server_status(host, port):
    """
    Attempts to establish a TCP connection to the Modbus server to check if it's running.
    """
    logger.debug(f"Checking server status for host {host} on port {port}")
    conn = asyncio.open_connection(host, port)
    try:
        reader, writer = await asyncio.wait_for(conn, timeout=3.0)
        writer.close()
        await writer.wait_closed()
        logger.info(
            f"Connection successful to host {host} on port {port}. Server is running."
        )
        return True
    except (asyncio.TimeoutError, OSError) as e:
        logger.debug(f"Connection failed to host {host} on port {port}: {e}")
        return False


async def _start_server_async(hostname, port):
    """
    Coroutine to start the Modbus TCP server.
    """
    logger.info(f"Attempting to start the Modbus server on {hostname}:{port}")
    if await check_server_status(hostname, port):
        logger.info("Modbus server is already running.")
        return

    try:
        await StartAsyncTcpServer(address=(hostname, port))
        logger.info("Modbus server started successfully.")
        frappe.db.set_value(
            "Modbus Server", "Modbus Server", "server_status", "Running"
        )
    except Exception as e:
        logger.error(f"Failed to start server on {hostname}:{port}: {e}")
        frappe.db.set_value("Modbus Server", "Modbus Server", "server_status", "Error")


def start_server():
    """
    Start the Modbus TCP server as a background job.
    """
    doc = frappe.get_single("Modbus Server")
    hostname = doc.hostname
    port = doc.port

    logger.debug(f"Enqueuing start server job for {hostname}:{port}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_start_server_async(hostname, port))


async def _stop_server_async(hostname, port):
    """
    Coroutine to stop the Modbus TCP server.
    """
    logger.info(f"Attempting to stop the Modbus server on {hostname}:{port}")
    if not await check_server_status(hostname, port):
        logger.info("Modbus server is not running. No need to stop.")
        frappe.db.set_value(
            "Modbus Server", "Modbus Server", "server_status", "Stopped"
        )
        return

    try:
        await ServerAsyncStop()
        logger.info("Modbus server stopped successfully.")
        frappe.db.set_value(
            "Modbus Server", "Modbus Server", "server_status", "Stopped"
        )
    except Exception as e:
        logger.error(f"Failed to stop server on {hostname}:{port}: {e}")
        frappe.db.set_value("Modbus Server", "Modbus Server", "server_status", "Error")


def stop_server():
    """
    Stop the Modbus TCP server as a background job.
    """
    doc = frappe.get_single("Modbus Server")
    hostname = doc.hostname
    port = doc.port

    logger.debug(f"Enqueuing stop server job for {hostname}:{port}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_stop_server_async(hostname, port))
