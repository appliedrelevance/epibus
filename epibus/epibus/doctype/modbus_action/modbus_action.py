# Copyright (c) 2022, Applied Relevance and contributors
# For license information, please see license.txt

from pprint import pprint
import frappe
from frappe.model.document import Document
from pymodbus.client import ModbusTcpClient
from frappe import get_all, _


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
        try:
            # Set up Modbus connection
            connection = frappe.get_doc("Modbus Connection", self.connection)
            client = ModbusTcpClient(connection.host, connection.port)
            if not client.connect():
                frappe.throw(
                    _("Failed to connect to Modbus server at {0}:{1}").format(
                        connection.host, connection.port
                    )
                )

            # Perform the Modbus action
            location = frappe.get_doc("Modbus Location", self.location)
            if self.action == "Write":
                response = client.write_coil(location.modbus_address, self.bit_value)
                action_result = _("Wrote {0} to location {1} on {2}:{3}").format(
                    self.bit_value, self.location, connection.host, connection.port
                )
            else:  # Assume action is "Read"
                response = client.read_coils(location.modbus_address, 1)
                action_result = _("Read value {0} from location {1}").format(
                    response.bits[0], self.location
                )

            # Disconnect the Modbus client
            client.close()

            # Add a timeline entry
            comment_text = _("Modbus Action '{0}' triggered: {1}").format(
                self.name, action_result
            )
            self.add_comment("Comment", text=comment_text)

            # Save the document to update the timeline
            self.save(ignore_permissions=True)

            return action_result

        except Exception as e:
            error_message = _("Failed to trigger Modbus Action '{0}': {1}").format(
                self.name, str(e)
            )
            # Log the error
            frappe.log_error(frappe.get_traceback(), "Modbus Action Trigger Error")

            # Add a timeline entry for the error
            self.add_comment("Comment", text=error_message)
            self.save(ignore_permissions=True)

            # Re-raise the exception
            raise e


@frappe.whitelist()
def handle_submit(doc, method):
    frappe.logger().info(
        "Handling submit for DocType: {0}, Name: {1}".format(doc.doctype, doc.name)
    )

    # Iterate through each item in the stock entry
    for item in doc.items:
        source_warehouse = item.s_warehouse

        if source_warehouse:
            frappe.logger().info(
                "Processing item with Source Warehouse: {0}".format(source_warehouse)
            )
            # Find Modbus Actions linked to this warehouse
            modbus_actions = frappe.get_all(
                "Modbus Action",
                filters={"Warehouse": source_warehouse},
                fields=["name"],
            )

            if modbus_actions:
                frappe.logger().info(
                    "Found Modbus Actions for Warehouse: {0}".format(source_warehouse)
                )
                # Trigger the Modbus Actions
                for action in modbus_actions:
                    modbus_action_doc = frappe.get_doc("Modbus Action", action.name)
                    try:
                        result = modbus_action_doc.trigger_action()
                        frappe.msgprint(
                            _("Modbus Action Triggered: {0}").format(result)
                        )
                        frappe.logger().info(
                            "Modbus Action Triggered: {0}".format(result)
                        )
                    except Exception as e:
                        frappe.log_error(
                            frappe.get_traceback(), "Modbus Action Trigger Error"
                        )
                        frappe.msgprint(
                            _("Failed to trigger Modbus Action: {0}").format(str(e))
                        )
                        frappe.logger().error(
                            "Error triggering Modbus Action: {0}".format(str(e))
                        )
            else:
                frappe.logger().info(
                    "No Modbus Actions found for Warehouse: {0}".format(
                        source_warehouse
                    )
                )
        else:
            frappe.logger().info("Skipped item with no Source Warehouse specified.")

    frappe.logger().info(
        "Completed handling submit for DocType: {0}, Name: {1}".format(
            doc.doctype, doc.name
        )
    )
