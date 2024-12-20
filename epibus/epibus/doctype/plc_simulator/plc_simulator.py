# Copyright (c) 2024, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from pymodbus.server.async_io import StartTcpServer
import asyncio
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading
from datetime import datetime
import socket
from contextlib import closing
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)

def check_port_available(port, host='localhost'):
    """Check if a port is available on the given host"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        try:
            sock.bind((host, port))
            return True
        except socket.error:
            return False

def find_available_port(start_port, max_attempts=100):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        if check_port_available(port):
            return port
    return None

class PLCSimulator(Document):
    def __init__(self, *args, **kwargs):
        super(PLCSimulator, self).__init__(*args, **kwargs)
        self.store = None
        self.server = None
        self.server_thread = None
        self._running = False
        self._status_update_in_progress = False
        self._shutdown_event = threading.Event()

        # Initialize io_points if needed
        if not hasattr(self, 'io_points'):
            self.io_points = []

    def get_server_status(self):
        """Get the current server status including running state"""
        return {
            'running': self._running,
            'connection_status': self.connection_status,
            'server_port': self.server_port if hasattr(self, 'server_port') else None
        }

    def validate(self):
        """Validate simulator settings"""
        if self.enabled:
            if not (1 <= self.server_port <= 65535):
                frappe.throw(_("Port number must be between 1 and 65535"))
            
            if not hasattr(self, 'io_points'):
                self.io_points = []
            
            self._validate_io_points()

    def _validate_io_points(self):
        """Validate IO point configurations"""
        address_map = {}
        for point in self.io_points:
            key = f"{point.signal_type}:{point.modbus_address}"
            if key in address_map:
                frappe.throw(_(
                    "Duplicate Modbus address {0} for signal type {1}"
                ).format(point.modbus_address, point.signal_type))
            address_map[key] = point

            # Validate address ranges based on signal type
            if not self._validate_address_range(point):
                frappe.throw(_(
                    "Invalid address {0} for signal type {1}"
                ).format(point.modbus_address, point.signal_type))

    def _validate_address_range(self, point):
        """Validate address range for a signal point"""
        addr = point.modbus_address
        if 'Digital' in point.signal_type:
            return 0 <= addr <= 1599
        elif 'Analog' in point.signal_type or 'Memory Register' in point.signal_type:
            return 0 <= addr <= 1023
        return False

    @frappe.whitelist()
    def start_simulator(self):
        """Start the Modbus TCP server"""
        if self._running:
            logger.info(f"Simulator {self.name} already running")
            return True

        try:
            # Reset shutdown event
            self._shutdown_event.clear()
            
            # Check port availability
            if not check_port_available(self.server_port):
                new_port = find_available_port(self.server_port + 1)
                if not new_port:
                    raise Exception(f"No available ports found after {self.server_port}")
                self.server_port = new_port
                self.db_set('server_port', new_port)

            # Initialize datastore and context
            context = self._initialize_datastore()
            
            # Start server thread
            self.server_thread = threading.Thread(
                target=self._run_server,
                args=(self.get("server_address", "localhost"),
                      self.server_port, context)
            )
            self.server_thread.daemon = True
            self.server_thread.start()

            # Update status and running state
            self._running = True
            success_msg = f"Simulator started on port {self.server_port}"
            self._update_status("Connected", success_msg)
            
            logger.info(success_msg)
            return True

        except Exception as e:
            logger.error(f"Failed to start simulator: {str(e)}", exc_info=True)
            self._update_status("Error", str(e))
            self._running = False
            return False

    @frappe.whitelist()
    def stop_simulator(self):
        """Stop the simulator and clean up resources"""
        logger.info(f"Stopping simulator {self.name}, current running state: {self._running}")
        
        try:
            # Signal shutdown
            self._shutdown_event.set()
            
            if hasattr(self, 'server') and self.server:
                logger.info("Shutting down server...")
                if hasattr(self.server, 'server_close'):
                    self.server.server_close()
                if hasattr(self.server, 'shutdown'):
                    self.server.shutdown()
                self.server = None

            if self.server_thread and self.server_thread.is_alive():
                logger.info("Waiting for server thread to terminate...")
                self.server_thread.join(timeout=5)
                if self.server_thread.is_alive():
                    logger.warning("Server thread did not terminate cleanly")
                self.server_thread = None

            if self.store:
                logger.info("Clearing datastore...")
                self.store = None

            # Update running state and status
            self._running = False
            self._update_status("Disconnected", "Simulator stopped")
            
            logger.info("Simulator stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Error stopping simulator: {str(e)}", exc_info=True)
            self._update_status("Error", f"Error stopping simulator: {str(e)}")
            return False

    def _run_server(self, host, port, context):
        """Run the Modbus TCP server with proper shutdown handling"""
        try:
            logger.info(f"Starting server loop on {host}:{port}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def start_server():
                try:
                    self.server = await StartTcpServer(
                        context=context,
                        address=(host, port)
                    )
                    logger.info(f"Server started on port {port}")
                    
                    # Keep server running until shutdown signaled
                    while not self._shutdown_event.is_set():
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"Server error: {str(e)}", exc_info=True)
                    self._update_status("Error", str(e))
                    raise
                finally:
                    if self.server:
                        self.server.server_close()
                        self.server = None
                    loop.stop()

            loop.create_task(start_server())
            loop.run_forever()
            
        except Exception as e:
            logger.error(f"Server loop error: {str(e)}", exc_info=True)
            self._update_status("Error", str(e))
        finally:
            self._running = False
            if not self._shutdown_event.is_set():
                self._update_status("Error", "Server stopped unexpectedly")

    def _update_status(self, status, message=None):
        """Update simulator status safely"""
        if self._status_update_in_progress:
            return

        try:
            self._status_update_in_progress = True
            logger.info(f"Updating status: {status} - {message}")

            # Update database
            self.db_set('connection_status', status)
            self.db_set('last_status_update', datetime.now())

            # Send realtime update
            frappe.publish_realtime(
                'simulator_status_update',
                {
                    'name': self.name,
                    'status': status,
                    'message': message,
                    'running': self._running
                },
                doctype='PLC Simulator',
                docname=self.name
            )

        except Exception as e:
            logger.error(f"Failed to update status: {str(e)}", exc_info=True)
        finally:
            self._status_update_in_progress = False

    @frappe.whitelist()
    def get_io_points(self):
        """Get current I/O points configuration"""
        return self.io_points if hasattr(self, 'io_points') else []

    def _initialize_datastore(self):
        """Initialize the Modbus datastore"""
        try:
            # Create data blocks with explicit sizes
            coils = ModbusSequentialDataBlock(0, [False] * 800)
            inputs = ModbusSequentialDataBlock(0, [False] * 800)
            input_registers = ModbusSequentialDataBlock(0, [0] * 1024)
            holding_registers = ModbusSequentialDataBlock(0, [0] * 1024)

            # Initialize values from io_points if they exist
            if hasattr(self, 'io_points') and self.io_points:
                for point in self.io_points:
                    addr = int(point.modbus_address)
                    value = point.value if point.value else '0'

                    try:
                        if 'Digital Output' in point.signal_type:
                            coils.setValues(addr, [bool(int(value))])
                        elif 'Digital Input' in point.signal_type:
                            inputs.setValues(addr, [bool(int(value))])
                        elif 'Analog Input' in point.signal_type:
                            input_registers.setValues(addr, [int(value)])
                        elif 'Analog Output' in point.signal_type or 'Memory Register' in point.signal_type:
                            holding_registers.setValues(addr, [int(value)])
                    except Exception as e:
                        logger.warning(
                            f"Failed to initialize point {point.location_name}: {str(e)}")

            # Create slave context without zero_mode
            self.store = ModbusSlaveContext(
                di=inputs,
                co=coils,
                ir=input_registers,
                hr=holding_registers
            )

            # Create and return server context
            return ModbusServerContext(slaves=self.store, single=True)

        except Exception as e:
            logger.error(f"Failed to initialize datastore: {str(e)}")
            raise

    def _run_server(self, host, port, context):
        """Run the Modbus TCP server with proper shutdown handling"""
        try:
            logger.info(f"Setting up server loop on {host}:{port}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Store the loop reference
            self.loop = loop

            async def run_server():
                try:
                    # Create server
                    logger.info("Creating TCP server")
                    self.server = await StartAsyncTcpServer(
                        context=context,
                        address=(host, port)
                    )
                    logger.info(f"TCP server started successfully on port {port}")

                    # Update running state and status after successful start
                    self._running = True
                    self._update_status("Connected", f"Server running on port {port}")

                    # Keep server running until stopped
                    while self._running:
                        await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Server error: {str(e)}", exc_info=True)
                    self._running = False
                    self._update_status("Error", str(e))
                    raise
                finally:
                    if hasattr(self, 'server') and self.server:
                        self.server.server_close()
                        self.server = None

            # Run the server using the event loop directly
            loop.run_until_complete(run_server())

        except Exception as e:
            if self._running:  # Only log if not shutting down
                logger.error(f"Server error: {str(e)}", exc_info=True)
                self._update_status("Error", str(e))
        finally:
            logger.info("Server loop exiting")
            self._running = False
            if hasattr(self, 'loop') and self.loop:
                self.loop.close()
            if self._running:  # Only update status if we weren't deliberately stopped
                self._update_status("Error", "Server stopped unexpectedly")

    def _update_status(self, status, message=None):
        """Update simulator status safely"""
        try:
            if not self._status_update_in_progress:
                logger.info(f"Updating status to {status} {message or ''}")
                self._status_update_in_progress = True
                try:
                    # Update running state
                    self._running = status == 'Connected'
                    
                    # Update database
                    frappe.db.set_value(
                        self.doctype,
                        self.name,
                        {
                            'connection_status': status,
                            'last_status_update': datetime.now()
                        },
                        update_modified=False
                    )
                    frappe.db.commit()

                    # Send realtime update
                    logger.info("Publishing realtime update")
                    frappe.publish_realtime(
                        event='simulator_status_update',
                        message={
                            'name': self.name,
                            'status': status,
                            'message': message,
                            'running': self._running
                        },
                        doctype='PLC Simulator',
                        docname=self.name
                    )
                finally:
                    self._status_update_in_progress = False

        except Exception as e:
            logger.error(f"Failed to update status: {str(e)}", exc_info=True)

    def _set_output(self, address, value):
        """Set digital output value"""
        if not self._running:
            return False

        try:
            self.store.setValues(fc=5, address=address, values=[value])
            return True
        except Exception as e:
            logger.error(f"Failed to set output {address}: {str(e)}")
            return False

    def _set_input(self, address, value):
        """Set digital input value"""
        if not self._running:
            return False

        try:
            self.store.setValues(fc=2, address=address, values=[value])
            return True
        except Exception as e:
            logger.error(f"Failed to set input {address}: {str(e)}")
            return False

    def _set_input_register(self, address, value):
        """Set input register value"""
        if not self._running:
            return False

        try:
            self.store.setValues(fc=4, address=address, values=[value])
            return True
        except Exception as e:
            logger.error(f"Failed to set input register {address}: {str(e)}")
            return False


@frappe.whitelist()
def get_simulators():
    """Get list of all PLC simulators with their status"""
    try:
        simulators = frappe.get_all(
            "PLC Simulator",
            fields=["name", "simulator_name", "equipment_type", "connection_status", 
                   "server_port", "enabled", "last_status_update"],
            order_by="simulator_name"
        )
        return simulators
    except Exception as e:
        logger.error(f"Error fetching simulators: {str(e)}")
        frappe.throw(_("Failed to fetch simulators"))