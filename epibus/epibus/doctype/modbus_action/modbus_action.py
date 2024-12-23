# Copyright (c) 2022, Applied Relevance and contributors
# For license information, please see license.txt

from pprint import pprint
import frappe
from frappe.model.document import Document
from pymodbus.client import ModbusTcpClient
from frappe import get_all, _
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)

class ModbusAction(Document):
    @frappe.whitelist()
    def test_action(self, host, port, action, location, bit_value):
        client = ModbusTcpClient(
                host=host,
                port=int(port),
                timeout=10
            )
        res = client.connect()
        # Throw an error if the connection fails
        if not res:
            frappe.throw("Connection Failed")
        # If the action is a write, wrote the bit_value to the location
        if action == "Write":
            print("Writing Modbus Action")
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
            resp = client.read_coils(location)
            retval = "On" if resp.bits[0] else "Off"
            self.bit_value = bool(resp.bits[0])
            return "Coil value at " + str(location) + " is " + retval

    @frappe.whitelist()
    def trigger_action(self):
        try:
            # Set up Modbus connection
            connection = frappe.get_doc("Modbus Connection", self.connection)
            client = ModbusTcpClient(
                host=connection.host,
                port=int(connection.port),
                timeout=10
            )
            if not client.connect():
                frappe.throw(
                    f"Failed to connect to Modbus server at {connection.host}:{connection.port}"
                )

            # Perform the Modbus action
            location = frappe.get_doc("Modbus Signal", self.location)
            if self.action == "Write":
                response = client.write_coil(location.modbus_address, self.bit_value)
                action_result = f"Wrote {self.bit_value} to location {location.modbus_address} modbus port {self.location} on {connection.host}:{connection.port}"
            else:  # Assume action is "Read"
                response = client.read_coils(location.modbus_address)
                action_result = f"Read value {response.bits[0]} from location {self.location}"

            # Disconnect the Modbus client
            client.close()

            # Add a timeline entry
            comment_text = f"Modbus Action '{self.name}' triggered: {action_result}"
            self.add_comment("Comment", text=comment_text)

            # Save the document to update the timeline
            self.save(ignore_permissions=True)

            return action_result

        except Exception as e:
            error_message = f"Failed to trigger Modbus Action '{self.name}': {e}"
            # Log the error
            frappe.log_error(frappe.get_traceback(), "Modbus Action Trigger Error")

            # Add a timeline entry for the error
            self.add_comment("Comment", text=error_message)
            self.save(ignore_permissions=True)

            # Re-raise the exception
            raise e


@frappe.whitelist()
def handle_submit(doc, method):
    logger.info(f"Handling submit for DocType: {doc.doctype}, Name: {doc.name}")

    if doc.doctype == "POS Invoice":
        # Iterate through each item in the stock entry
        for item in doc.items:
            move_from_warehouse(item.warehouse)
    elif doc.doctype == "Stock Entry":
        for item in doc.items:
            move_from_warehouse(item.s_warehouse)
    elif doc.doctype == "Pick List":
        for item in doc.locations:
            move_from_warehouse(item.warehouse)
    else:
        frappe.log_error(f"Modbus Actions are not defined for {doc.doctype}") 
    logger.info(f"Completed handling submit for DocType: {doc.doctype}, Name: {doc.name}")

def move_from_warehouse(warehouse):
    if warehouse:
        logger.info(f"Processing item with Source Warehouse: {warehouse}")
        # Find Modbus Actions linked to this warehouse
        modbus_actions = frappe.get_all(
            "Modbus Action",
             filters={"Warehouse": warehouse},
             fields=["name"],
        )

        if modbus_actions:
            logger.info(
                f"Found Modbus Actions for Warehouse: {warehouse}"
            )
            # Trigger the Modbus Actions
            for action in modbus_actions:
                modbus_action_doc = frappe.get_doc("Modbus Action", action.name)
                try:
                    result = modbus_action_doc.trigger_action()
                    frappe.msgprint(
                        f"Modbus Action Triggered: {result}"
                    )
                    logger.info(
                        f"Modbus Action Triggered: {result}"
                    )
                except Exception as e:
                    frappe.log_error(
                        frappe.get_traceback(), "Modbus Action Trigger Error"
                    )
                    frappe.msgprint(
                        f"Failed to trigger Modbus Action: {e}"
                    )
                    frappe.logger().error(
                        f"Error triggering Modbus Action: {e}"
                    )
        else:
            logger.info(f"No Modbus Actions found for Warehouse: {warehouse}")
    else:
        logger.info("Skipped item with no Source Warehouse specified.")

