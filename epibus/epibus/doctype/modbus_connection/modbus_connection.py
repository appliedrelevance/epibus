# Copyright (c) 2022, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from pymodbus.client import ModbusTcpClient


class ModbusConnection(Document):
    @frappe.whitelist()
    def test_connection(self, host, port):
        client = ModbusTcpClient(host, port)

        return "Connection successful" if client.connect() else "Connection failed"
