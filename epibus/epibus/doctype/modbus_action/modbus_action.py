# Copyright (c) 2022, Applied Relevance and contributors
# For license information, please see license.txt

from pprint import pprint
import frappe
from frappe.model.document import Document
from pymodbus.client import ModbusTcpClient


class ModbusAction(Document):
    @frappe.whitelist()
    def test_action(self, host, port, action, location, bit_value):
        client = ModbusTcpClient(host, port)
        res = client.connect()
        # Throw an error if the connection fails
        if not res:
            frappe.throw('Connection Failed')
        # If the action is a write, wrote the bit_value to the location
        if action == "Write":
            resp = client.write_coil(location, bit_value)
            return "Wrote " + str(resp.value) + " to location " + str(resp.address) + " on " + str(host) + ":" + str(port)
        else:  # If the action is a read, read the value from the location
            resp = client.read_coils(location, 1)
            retval = "On" if resp.bits[0] else "Off"
            self.bit_value = bool(resp.bits[0])
            return "Coil value at " + str(location) + " is " + retval

    @frappe.whitelist()
    def trigger_action(self):
        print('Triggering Modbus Action ' + self.name)
        pprint(self.as_dict())
        connection = frappe.get_doc(
            "Modbus Connection", self.connection)
        host = connection.host
        port = connection.port
        action = self.action
        location = int(self.location)
        bit_value = self.bit_value
        client = ModbusTcpClient(host, port)
        res = client.connect()
        # Throw an error if the connection fails
        if not res:
            frappe.throw('Connection Failed')
            # If the action is a write, write the bit_value to the location
        if action == "Write":
            resp = client.write_coil(location, bit_value)
            return "Wrote " + str(resp.value) + " to location " + str(resp.address) + " on " + str(host) + ":" + str(port)
        else:  # If the action is a read, read the value from the location
            resp = client.read_coils(location, 1)
            retval = "On" if resp.bits[0] else "Off"
            self.bit_value = bool(resp.bits[0])
            return "Coil value at " + str(location) + " is " + retval
