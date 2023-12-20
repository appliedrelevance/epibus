# Copyright (c) 2022, Applied Relevance and contributors
# For license information, please see license.txt

from pprint import pprint
import frappe
from frappe.model.document import Document
from pymodbus.client import ModbusTcpClient
import logging

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModbusAction(Document):
    @frappe.whitelist()
    def test_action(self, host, port, action, location, bit_value):
        """
        Test action for Modbus communication.
        Connects to the Modbus server and performs read or write operations based on the action specified.

        :param host: Host address of the Modbus server.
        :param port: Port number for the Modbus connection.
        :param action: The action to be performed - 'Read' or 'Write'.
        :param location: The Modbus coil location.
        :param bit_value: The value to be written, applicable for write action.
        :return: A string describing the result of the operation.
        """
        client = ModbusTcpClient(host, port)
        res = client.connect()

        if not res:
            error_msg = "Connection Failed to host: {}, port: {}".format(host, port)
            logger.error(error_msg)
            frappe.throw(error_msg)

        if action == "Write":
            resp = client.write_coil(location, bit_value)
            result = "Wrote {} to location {} on {}:{}".format(bit_value, location, host, port)
            logger.info(result)
            return result
        else:
            resp = client.read_coils(location, 1)
            retval = "On" if resp.bits[0] else "Off"
            self.bit_value = bool(resp.bits[0])
            result = "Coil value at {} is {}".format(location, retval)
            logger.info(result)
            return result

    @frappe.whitelist()
    def trigger_action(self):
        """
        Triggers a Modbus action based on the settings specified in the ModbusAction document.

        Retrieves connection details and executes the Modbus action.
        """
        logger.info(f"Triggering Modbus Action {self.name}")
        pprint(self.as_dict())

        connection = frappe.get_doc("Modbus Connection", self.connection)
        host = connection.host
        port = connection.port
        action = self.action
        location_name = self.location

        location = frappe.get_doc("Modbus Location", location_name)
        logger.info("Location: " + str(location.as_dict()))

        if not location:
            error_msg = "Location not found: " + location_name
            logger.error(error_msg)
            frappe.throw(error_msg)

        address = location.modbus_address
        bit_value = self.bit_value

        client = ModbusTcpClient(host, port)
        res = client.connect()

        if not res:
            error_msg = "Connection Failed to host: {}, port: {}".format(host, port)
            logger.error(error_msg)
            frappe.throw(error_msg)

        if action == "Write":
            resp = client.write_coil(address, bit_value)
            result = "Wrote {} to location {} on {}:{}".format(bit_value, location_name, host, port)
            logger.info(result)
            return result
        else:
            logger.info("Reading coils from " + str(location_name))
            resp = client.read_coils(address, 1)
            retval = "On" if resp.bits[0] else "Off"
            self.bit_value = bool(resp.bits[0])
            result = "Coil value at {} is {}".format(location_name, retval)
            logger.info(result)
            return result

# Event Handlers

def handle_submit(doc, method):
    """
    Handler for document submission event.
    Executes the Modbus action if needed.

    :param doc: The document being submitted.
    :param method: The method being called (submit).
    """
    execute_action_if_needed(doc, method)

def handle_cancel(doc, method):
    """
    Handler for document cancellation event.
    Executes the Modbus action if needed.

    :param doc: The document being canceled.
    :param method: The method being called (cancel).
    """
    execute_action_if_needed(doc, method)

def handle_update(doc, method):
    """
    Handler for document update event.
    Executes the Modbus action if needed.

    :param doc: The document being updated.
    :param method: The method being called (update).
    """
    execute_action_if_needed(doc, method)

def execute_action_if_needed(doc, method):
    """
    Executes the Modbus action based on the provided document and method.
    Checks the Modbus settings before proceeding.

    :param doc: The document related to the action.
    :param method: The method (submit, cancel, update) triggering the action.
    """
    settings = frappe.get_doc("Modbus Settings")
    if not settings.enable_triggers:
        return

    human_readable_method = method.replace("_", " ").title()
    filters = {"event_trigger": human_readable_method, "linked_doctype": doc.doctype}
    matching_actions = frappe.get_all("Modbus Action", filters=filters)

    for action in matching_actions:
        action_doc = frappe.get_doc("Modbus Action", action.name)
        logger.debug(f"Type of action_doc: {type(action_doc)}")
        logger.debug(f"Methods available in action_doc: {dir(action_doc)}")

        if hasattr(action_doc, "trigger_action"):
            action_doc.trigger_action()
        else:
            logger.warning(f"'trigger_action' not found in action_doc")
