# Copyright (c) 2022, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from pymodbus.client import ModbusTcpClient


class ModbusConnection(Document):
    @frappe.whitelist()
    def test_connection(self, host, port):
        print('Testing Modbus Connection ' + self.name)
        client = ModbusTcpClient(host, port)
        print('Connecting to ' + host + ":" + str(port))
        res = client.connect()
        locs = "Locations: "
        for d in self.get("locations"):
            stateBln = client.read_coils(d.modbus_address, 1).bits[0];
            state = "On" if stateBln else "Off"
            if d.modbus_address is None or d.plc_address is None:
                locs += "Not Configured, "
            else:
                locs += str(d.location_name) + ": " + \
                    str(d.plc_address) + " (" + state + "), "
            d.value = state
            d.toggle = stateBln;
        return "Connection successful " + locs if res else "Connection failed"
    @frappe.whitelist()
    def toggle_location(self, host, port, modbus_address, location_type):
        print('Toggling ' + str(modbus_address))
        client = ModbusTcpClient(host, port)
        res = client.connect()
        if res:
            state = client.read_coils(modbus_address, 1).bits[0];
            print('Current state: ' + str(state))
            client.write_coil(modbus_address, not state)
            client.close()
            print("Toggled from " + str(state) + " to " + str(not state))
        else:
            return "Connection Failed"
