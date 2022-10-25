# Copyright (c) 2022, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from pymodbus.client import ModbusTcpClient


class ModbusConnection(Document):
    @frappe.whitelist()
    def test_connection(self, host, port):
        client = ModbusTcpClient(host, port)
        res = client.connect()
        locs = "Locations: "
        for d in self.get("locations"):
            state = "On" if client.read_coils(
                d.modbus_address, 1).bits[0] else "Off"
            locs += d.device_address + ": " + \
                d.plc_address + " (" + state + "), "
            d.value = state
        return "Connection successful " + locs if res else "Connection failed"
