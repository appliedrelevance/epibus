# Copyright (c) 2024, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading
from datetime import datetime
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)

class ModbusSimulator(Document):
    def __init__(self, *args, **kwargs):
        super(ModbusSimulator, self).__init__(*args, **kwargs)
        self.store = None
        self.server = None
        self.server_thread = None
        self._running = False
        self._status_update_in_progress = False

    def validate(self):
        """Validate simulator settings"""
        if self.enabled:
            if not (1 <= self.server_port <= 65535):
                frappe.throw(_("Port number must be between 1 and 65535"))

    def on_update(self):
        """Handle changes to simulator settings"""
        if not self._status_update_in_progress:  
            if self.enabled and not self._running:
                self.start_simulator()
            elif not self.enabled and self._running:
                self.stop_simulator()

    def after_insert(self):
        """Initialize simulator after first creation"""
        if self.enabled:
            self.start_simulator()

    def on_trash(self):
        """Clean up simulator resources"""
        if self._running:
            self.stop_simulator()

    @frappe.whitelist()
    def start_simulator(self):
        """Start the Modbus TCP server"""
        if self._running:
            return False

        try:
            context = self._initialize_datastore()
            self.server_thread = threading.Thread(
                target=self._run_server,
                args=(self.get("server_address", "localhost"),
                        self.server_port, context)
            )
            self.server_thread.daemon = True
            self.server_thread.start()

            self._running = True
            self._update_status("Connected")
            return True

        except Exception as e:
            logger.error(f"Failed to start simulator: {str(e)}")
            self._update_status("Error", str(e))
            return False

    @frappe.whitelist()
    def stop_simulator(self):
        """Stop the simulator"""
        if not self._running:
            return False

        try:
            self._running = False
            self._update_status("Disconnected")
            return True

        except Exception as e:
            logger.error(f"Failed to stop simulator: {str(e)}")
            self._update_status("Error", str(e))
            return False

    def _initialize_datastore(self):
        """Initialize the Modbus datastore"""
        try:
            # Create data blocks with explicit sizes
            coils = ModbusSequentialDataBlock(0, [False] * 800)
            inputs = ModbusSequentialDataBlock(0, [False] * 800)
            input_registers = ModbusSequentialDataBlock(0, [0] * 1024)
            holding_registers = ModbusSequentialDataBlock(0, [0] * 1024)

            self.store = ModbusSlaveContext(
                di=inputs,
                co=coils,
                ir=input_registers,
                hr=holding_registers
            )

            return ModbusServerContext(slaves=self.store, single=True)

        except Exception as e:
            logger.error(f"Failed to initialize datastore: {str(e)}")
            raise

    def _run_server(self, host, port, context):
        """Run the Modbus TCP server"""
        try:
            StartTcpServer(context, address=(host, port))
        except Exception as e:
            logger.error(f"Server error: {str(e)}")
            self._update_status("Error", str(e))

    def _update_status(self, status, message=None):
        """Update simulator status safely"""
        try:
            if not self._status_update_in_progress and self.connection_status != status:
                self._status_update_in_progress = True
                try:
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

                    frappe.publish_realtime(
                        event='modbus_simulator_status_update',
                        message={
                            'name': self.name,
                            'status': status,
                            'message': message
                        },
                        doctype='Modbus Simulator',
                        docname=self.name
                    )
                finally:
                    self._status_update_in_progress = False

        except Exception as e:
            logger.error(f"Failed to update status: {str(e)}")