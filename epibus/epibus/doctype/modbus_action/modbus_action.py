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
    def trigger_action(self):
        print(f"Triggering Modbus Action {self.name}")
        pprint(self.as_dict())
        connection = frappe.get_doc("Modbus Connection", self.connection)
        host = connection.host
        port = connection.port
        action = self.action
        location_name = self.location
        # Get the Location document
        location = frappe.get_doc("Modbus Location", location_name)
        print("Location: " + str(location.as_dict()))
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
            print("Reading coils from " + str(location_name))
            resp = client.read_coils(address, 1)
            retval = "On" if resp.bits[0] else "Off"
            self.bit_value = bool(resp.bits[0])
            return "Coil value at " + str(location_name) + " is " + retval


# Event Handlers
def handle_submit(doc, method):
    execute_action_if_needed(doc, method)


def handle_cancel(doc, method):
    execute_action_if_needed(doc, method)


def handle_update(doc, method):
    execute_action_if_needed(doc, method)


def execute_action_if_needed(doc, method):
    # First, check if the feature is activated from the singleton DocType
    settings = frappe.get_doc("Modbus Settings")
    if not settings.enable_triggers:
        return
    # Translate the method into a human-readable format.
    # This assumes your 'Event Trigger' options in the Doctype are "On Save", "On Submit", and "On Cancel"
    human_readable_method = method.replace("_", " ").title()

    # Filter Modbus Actions based on the triggering event and the linked Doctype
    filters = {"event_trigger": human_readable_method, "linked_doctype": doc.doctype}

    # Find matching Modbus Actions based on filters
    matching_actions = get_all("Modbus Action", filters=filters)

    # Loop through all matching Modbus Actions and trigger them
    for action in matching_actions:
        action_doc = frappe.get_doc("Modbus Action", action.name)

        # Diagnostic code
        print(f"Type of action_doc: {type(action_doc)}")
        print(f"Methods available in action_doc: {dir(action_doc)}")

        # Trigger action
        if hasattr(action_doc, "trigger_action"):
            action_doc.trigger_action()
        else:
            print(f"'trigger_action' not found in action_doc")
