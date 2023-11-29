# Copyright (c) 2022, Applied Relevance and contributors
# For license information, please see license.txt

from pprint import pprint
import frappe
from frappe.model.document import Document
from pymodbus.client import ModbusTcpClient
from frappe import get_all


class ModbusAction(Document):
    @frappe.whitelist()
    def test_action(self, host, port, action, location, bit_value):
        client = ModbusTcpClient(host, port)
        res = client.connect()
        # Throw an error if the connection fails
        if not res:
            frappe.throw("Connection Failed")
        # If the action is a write, wrote the bit_value to the location
        if action == "Write":
            resp = client.write_coil(location, bit_value)
            return (
                "Wrote "
                + str(bit_value)
                + " to location "
                + str(location)
                + " on "
                + str(host)
                + ":"
                + str(port)
            )
        else:  # If the action is a read, read the value from the location
            resp = client.read_coils(location, 1)
            retval = "On" if resp.bits[0] else "Off"
            self.bit_value = bool(resp.bits[0])
            return "Coil value at " + str(location) + " is " + retval

    @frappe.whitelist()
    def trigger_action(self, source_doc=None):
        print(f"Triggering Modbus Action {self.name}")
        source_doc.add_comment("Comment", f"Triggering Modbus Action {self.name}")
        self.add_comment("Comment", f"Triggering Modbus Action {self.name} on source_doc {source_doc.name}")
        connection = frappe.get_doc("Modbus Connection", self.connection)
        host = connection.host
        port = connection.port
        action = self.action
        location_name = self.location

        # Get the Location document
        location = frappe.get_doc("Modbus Location", location_name)
        if not location:
            frappe.throw("Location not found: " + location_name)

        address = location.modbus_address
        bit_value = self.bit_value

        client = ModbusTcpClient(host, port)
        res = client.connect()

        # Throw an error if the connection fails
        if not res:
            frappe.throw("Connection Failed")

        # If the action is a write, write the bit_value to the location
        if action == "Write":
            print(f"Writing {bit_value} to location {location_name} on {host}:{port}")
            source_doc.add_comment("Comment", f"Writing {bit_value} to location {location_name} on {host}:{port}")
            resp = client.write_coil(address, bit_value)
            return (
                "Wrote "
                + str(bit_value)
                + " to location "
                + str(location_name)
                + " on "
                + str(host)
                + ":"
                + str(port)
            )
        else:  # If the action is a read, read the value from the location
            print(f"Reading value from location {location_name} on {host}:{port}")
            resp = client.read_coils(address, 1)
            retval = "On" if resp.bits[0] else "Off"
            self.bit_value = bool(resp.bits[0])
            source_doc.add_comment("Comment", f"Read {retval} from location {location_name} on {host}:{port}")
            return "Coil value at " + str(location_name) + " is " + retval
    @frappe.whitelist()
    def get_fields(self, doctype):
        fields = []
        meta = frappe.get_meta(doctype)
        for field in meta.fields:
            fields.append(field.fieldname)
            if field.fieldtype == 'Table':
                child_meta = frappe.get_meta(field.options)
                for child_field in child_meta.fields:
                    fields.append(f"{field.fieldname}.{child_field.fieldname}")
        return fields
