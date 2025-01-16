# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from pymodbus.server import StartTcpServer
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.client import ModbusTcpClient
import threading
import time
from datetime import datetime
from epibus.epibus.utils.epinomy_logger import get_logger
import asyncio
from frappe.utils import now_datetime

logger = get_logger(__name__)


class ModbusSimulator(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from epibus.epibus.doctype.modbus_signal.modbus_signal import ModbusSignal
        from frappe.types import DF

        active_connections: DF.Int
        auto_start: DF.Check
        debug_mode: DF.Check
        description: DF.SmallText | None
        enabled: DF.Check
        equipment_type: DF.Literal[
            "Robot", "Conveyor", "PLC", "Sensor Array", "Machine Tool", "Custom"
        ]
        error_message: DF.SmallText | None
        io_points: DF.Table[ModbusSignal]
        last_status_update: DF.Datetime | None
        reconnect_delay: DF.Int
        response_timeout: DF.Int
        server_port: DF.Int
        server_script: DF.Link | None
        server_status: DF.Literal["Stopped", "Starting", "Running", "Stopping", "Error"]
        server_uptime: DF.Duration | None
        simulator_name: DF.Data
    # end: auto-generated types
    """ModbusSimulator manages a Modbus TCP server instance for device simulation.

    This class provides functionality to:
    - Start/Stop a Modbus TCP server
    - Monitor server status and connections
    - Initialize and manage Modbus data storage
    - Handle clean shutdown and error recovery
    """

    def __init__(self, *args, **kwargs):
        """Initialize simulator object."""
        super(ModbusSimulator, self).__init__(*args, **kwargs)
        self.store = None
        self.server = None
        self.server_thread = None
        self._start_time = None
        self._status_update_in_progress = False
        self._stop_event = threading.Event()

    def validate(self):
        """Validate simulator settings before save."""
        if not self._status_update_in_progress:
            # Validate port range
            if not (1 <= self.server_port <= 65535):
                frappe.throw("Port must be between 1 and 65535")

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
                frappe.throw("Cannot change port while server is running")

            if (
                self.has_value_changed("enabled")
                and not self.enabled
                and self.server_status == "Running"
            ):
                frappe.throw("Stop the server before disabling")

    def on_update(self):
        """Handle changes to simulator settings."""
        if not self._status_update_in_progress:
            if self.enabled and self.auto_start and self.server_status == "Stopped":
                self.start_simulator()
            elif not self.enabled and self.server_status == "Running":
                self.stop_simulator()

    def after_insert(self):
        """Initialize simulator after first creation."""
        if self.enabled and self.auto_start:
            self.start_simulator()

    def on_trash(self):
        """Clean up simulator resources."""
        if self.server_status == "Running":
            self.stop_simulator()

    @frappe.whitelist()
    def start_simulator(self):
        """Start the Modbus TCP server."""
        logger.info(f"Start simulator request received for {self.simulator_name}")

        if self.server_status == "Running":
            logger.warning("Cannot start - server is already running")
            return {"success": False, "error": "Server is already running"}

        try:
            # Reset if in bad state
            if self.server_status not in ["Stopped", "Error"]:
                logger.warning(f"Resetting invalid server status: {self.server_status}")
                self._update_status("Stopped")
                frappe.db.commit()

            # Initialize server
            self._update_status("Starting")
            context = self._initialize_datastore()

            # Start server thread
            self._stop_event.clear()
            self.server_thread = threading.Thread(
                target=self._run_server_loop, args=(self.server_port, context)
            )
            self.server_thread.daemon = True

            logger.debug("Starting server thread")
            self.server_thread.start()

            # Verify startup
            time.sleep(0.5)
            if not self.server_thread.is_alive():
                logger.error("Server thread failed to start")
                self._update_status("Error", "Server thread failed to start")
                return {"success": False, "error": "Server thread failed to start"}

            self._start_time = datetime.now()
            self._update_status("Running")

            logger.info(f"Successfully started simulator {self.simulator_name}")
            return {"success": True}

        except Exception as e:
            error_msg = f"Failed to start simulator: {str(e)}"
            logger.error(error_msg)
            self._cleanup_server()
            self._update_status("Error", error_msg)
            frappe.db.commit()
            return {"success": False, "error": error_msg}

    @frappe.whitelist()
    def stop_simulator(self):
        """Stop the simulator."""
        logger.info(f"Stop simulator request received for {self.simulator_name}")

        if self.server_status == "Stopped":
            return {"success": False, "error": "Server is not running"}

        try:
            self._update_status("Stopping")
            self._cleanup_server()

            logger.debug("Setting final status to Stopped")
            self._update_status("Stopped")
            frappe.db.commit()

            logger.info(f"Successfully stopped simulator {self.simulator_name}")
            return {"success": True}

        except Exception as e:
            error_msg = f"Failed to stop simulator: {str(e)}"
            logger.error(error_msg)
            self._update_status("Error", error_msg)
            frappe.db.commit()
            return {"success": False, "error": error_msg}

    def _initialize_datastore(self):
        """Initialize the Modbus datastore."""
        try:
            # Create data blocks with explicit sizes
            coils = ModbusSequentialDataBlock(0, [False] * 1000)
            discrete_inputs = ModbusSequentialDataBlock(0, [False] * 1000)
            holding_registers = ModbusSequentialDataBlock(0, [0] * 1000)
            input_registers = ModbusSequentialDataBlock(0, [0] * 1000)

            # Create slave context
            self.store = ModbusSlaveContext(
                di=discrete_inputs,
                co=coils,
                hr=holding_registers,
                ir=input_registers,
            )

            return ModbusServerContext(slaves=self.store, single=True)

        except Exception as e:
            logger.error(f"Failed to initialize datastore: {str(e)}")
            raise

    def _run_server_loop(self, port, context):
        """Run the Modbus TCP server."""
        try:
            if self.debug_mode:
                logger.debug(f"Starting Modbus server on 127.0.0.1:{port}")

            # Create and start server without defer_start
            identity = ModbusDeviceIdentification(
                info_name={
                    "VendorName": "EpiBus Simulator",
                    "ProductCode": "MBSIM",
                    "ModelName": self.simulator_name,
                    "MajorMinorRevision": "1.0",
                }
            )

            self.server = StartTcpServer(
                context=context,
                address=("127.0.0.1", port),
                identity=identity,
                # Removed timeout parameter
            )

            # Server is now running, update status to Running
            self._update_status("Running")

            # Loop until stop requested
            while not self._stop_event.is_set():
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"Server error: {str(e)}")
            self._update_status("Error", str(e))
        finally:
            if self.debug_mode:
                logger.debug("Server shutdown complete")
            self._update_status("Stopped")

    def _cleanup_server(self):
        """Clean up server resources."""
        try:
            if self._stop_event:
                self._stop_event.set()

            if self.server:
                try:
                    # Give server time to shutdown gracefully
                    time.sleep(0.5)
                    if hasattr(self.server, "socket"):
                        self.server.socket.close()
                    if hasattr(self.server, "server_close"):
                        self.server.server_close()
                except:
                    pass
                self.server = None

            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=2)
                if self.server_thread.is_alive():
                    logger.warning("Server thread did not exit cleanly")

            self.server_thread = None
            self._start_time = None

        except Exception as e:
            logger.error(f"Error during server cleanup: {str(e)}")
            raise

    def _update_status(self, status, message=None):
        """Update simulator status safely."""
        try:
            if not self._status_update_in_progress:
                self._status_update_in_progress = True
                try:
                    # Calculate uptime
                    uptime = 0.0
                    if self._start_time and status == "Running":
                        delta = now_datetime() - self._start_time
                        uptime = delta.total_seconds()  # Convert to seconds

                    # Get current time in local timezone
                    now = now_datetime()

                    # Build update dictionary
                    update_dict = {
                        "server_status": status,
                        "last_status_update": (
                            now if status == "Running" else self.last_status_update
                        ),
                        "error_message": message if status == "Error" else None,
                        "server_uptime": uptime,
                        "active_connections": 1 if status == "Running" else 0,
                        "docstatus": 1 if status == "Running" else 0,
                    }

                    if status == "Running":
                        update_dict["enabled"] = 1

                    # Update document
                    logger.debug(f"Updating document with: {update_dict}")
                    self.db_set(update_dict, update_modified=False)
                    frappe.db.commit()

                    # Publish realtime update
                    frappe.publish_realtime(
                        "simulator_status_update",
                        {
                            "name": self.name,
                            "status": status,
                            "message": message,
                            "uptime": uptime,
                            "connections": update_dict["active_connections"],
                            "docstatus": update_dict["docstatus"],
                        },
                        doctype="Modbus Simulator",
                        docname=self.name,
                    )

                finally:
                    self._status_update_in_progress = False

        except Exception as e:
            logger.error(f"Failed to update status: {str(e)}")

    @frappe.whitelist()
    def test_modbus_signals(self):
        """Test connection to the simulator using pymodbus client."""
        try:
            # Ensure an event loop exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            if self.server_status != "Running":
                return {"success": False, "error": "Simulator is not running"}

            client = ModbusTcpClient("127.0.0.1", port=self.server_port)
            if not client.connect():
                return {"success": False, "error": "Could not connect to simulator"}

            results = []
            for signal in self.io_points:
                modbus_address = signal.modbus_address
                try:
                    if signal.signal_type == "Digital Output Coil":
                        # Read single coil instead of 8
                        response = client.read_coils(modbus_address, count=1)
                    elif signal.signal_type == "Digital Input Contact":
                        response = client.read_discrete_inputs(modbus_address, count=1)
                    elif signal.signal_type == "Analog Input Register":
                        response = client.read_input_registers(modbus_address, count=1)
                    elif (
                        signal.signal_type == "Analog Output Register"
                        or signal.signal_type == "Holding Register"
                    ):
                        response = client.read_holding_registers(
                            modbus_address, count=1
                        )
                    else:
                        continue

                    if response.isError():
                        results.append(
                            {"signal": signal.signal_name, "error": str(response)}
                        )
                    else:
                        # Extract single value instead of array
                        value = (
                            response.bits[0]
                            if signal.signal_type
                            in ["Digital Output Coil", "Digital Input Contact"]
                            else response.registers[0]
                        )
                        results.append(
                            {
                                "signal": signal.signal_name,
                                "value": value,
                                "type": signal.signal_type,
                            }
                        )
                        logger.debug(f"Signal {signal.signal_name} read: {value}")

                except Exception as e:
                    logger.error(f"Error reading signal {signal.signal_name}: {str(e)}")
                    results.append({"signal": signal.signal_name, "error": str(e)})

            client.close()
            return {"success": True, "results": results}

        except Exception as e:
            logger.error(f"Modbus signal test failed: {str(e)}")
            return {"success": False, "error": str(e)}


# Ensure an event loop is created and set in the current thread
def ensure_event_loop():
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)


# Call ensure_event_loop before running any asyncio code
ensure_event_loop()


@frappe.whitelist()
def test_connection(simulator_name):
    """Test connection to the simulator."""
    try:
        simulator = frappe.get_doc("Modbus Simulator", simulator_name)

        if simulator.server_status != "Running":
            return {"success": False, "error": "Simulator is not running"}

        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)

        result = sock.connect_ex(("127.0.0.1", simulator.server_port))
        sock.close()

        if result == 0:
            return {
                "success": True,
                "message": f"Successfully connected to port {simulator.server_port}",
            }
        else:
            return {
                "success": False,
                "error": f"Could not connect to port {simulator.server_port}",
            }

    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return {"success": False, "error": str(e)}
