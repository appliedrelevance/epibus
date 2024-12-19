# Copyright (c) 2024, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PLCSimulator(Document):
	def __init__(self, *args, **kwargs):
		super(PLCSimulator, self).__init__(*args, **kwargs)
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
		if not self._status_update_in_progress:  # Only process if not from status update
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
			# Initialize datastore
			context = self._initialize_datastore()

			# Start server thread
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

	@frappe.whitelist()
	def get_io_points(self):
		"""Get all I/O points for this simulator"""
		try:
			return self.io_points
		except Exception as e:
			logger.error(f"Failed to get I/O points: {str(e)}")
			return []

	def _initialize_datastore(self):
		"""Initialize the Modbus datastore"""
		try:
			# Create data blocks with explicit sizes
			coils = ModbusSequentialDataBlock(0, [False] * 800)
			inputs = ModbusSequentialDataBlock(0, [False] * 800)
			input_registers = ModbusSequentialDataBlock(0, [0] * 1024)
			holding_registers = ModbusSequentialDataBlock(0, [0] * 1024)

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
					# Update fields directly in the database without triggering form reloads
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

					# Only publish realtime update if status actually changed
					frappe.publish_realtime(
						event='plc_simulator_status_update',
						message={
							'name': self.name,
							'status': status,
							'message': message
						},
						doctype='PLC Simulator',
						docname=self.name
					)
				finally:
					self._status_update_in_progress = False

		except Exception as e:
			logger.error(f"Failed to update status: {str(e)}")

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
