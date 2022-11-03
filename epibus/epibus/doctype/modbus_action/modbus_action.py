# Copyright (c) 2022, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from pymodbus.client import ModbusTcpClient
import pprint


class ModbusAction(Document):
    @frappe.whitelist()
    def test_action(self, host, port, action, location, bit_value):
        print(action + "ing location " + str(location) +
              " on " + str(host) + ":" + str(port))
        client = ModbusTcpClient(host, port)
        res = client.connect()
        if not res:
            return 'Connection Failed'
        if action == "Write":
            # cmd = 0xFF00 if bit_value else 0x0000
            resp = client.write_coil(location, bit_value)
            return "Wrote " + str(resp.value) + " to location " + str(resp.address) + " on " + str(host) + ":" + str(port)
        else:
            resp = client.read_coils(location, 1)
            retval = "On" if resp.bits[0] else "Off"
            self.bit_value = bool(resp.bits[0])
            return "Coil value at " + str(location) + " is " + retval
