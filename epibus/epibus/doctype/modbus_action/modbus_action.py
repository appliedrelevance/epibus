# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.core.doctype.server_script.server_script import ServerScript
from frappe import _
from typing import cast

from epibus.epibus.utils.epinomy_logger import get_logger
logger = get_logger(__name__)


class ModbusAction(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from epibus.epibus.doctype.modbus_parameter.modbus_parameter import ModbusParameter
        from frappe.types import DF

        action_name: DF.Data
        api_method: DF.Data | None
        connection: DF.Link
        cron_format: DF.Data | None
        description: DF.SmallText | None
        doctype_event: DF.Literal["Before Insert", "After Insert", "Before Save", "After Save", "Before Submit", "After Submit", "Before Cancel", "After Cancel", "Before Delete", "After Delete", "Before Save (Submitted Document)", "After Save (Submitted Document)"]
        enabled: DF.Check
        event_frequency: DF.Literal["All", "Hourly", "Daily", "Weekly", "Monthly", "Yearly", "Hourly Long", "Daily Long", "Weekly Long", "Monthly Long", "Cron"]
        modbus_signal: DF.Link
        parameters: DF.Table[ModbusParameter]
        reference_doctype: DF.Link | None
        script_type: DF.Literal["DocType Event", "Scheduler Event", "Signal Change", "API"]
        server_script: DF.Link
        signal_condition: DF.Literal["Any Change", "Equals", "Greater Than", "Less Than"]
        signal_value: DF.Data | None
    # end: auto-generated types

    def validate(self):
        if not self.connection:
            frappe.throw(_("Modbus Connection is required"))

        if not self.server_script:
            frappe.throw(_("Server Script is required"))

        # Validate script type
        self.validate_script_type()

    def validate_script_type(self):
        """Validate the script type of the linked server script"""
        script: ServerScript = cast(ServerScript, frappe.get_doc(
            "Server Script", self.server_script))
        if script.script_type not in ("API"):
            frappe.throw(_("Server Script must be of type API"))

    @frappe.whitelist(methods=['POST'])
    def execute_script(self, event_doc=None):
        """Execute the linked server script"""
        logger.debug(
            f"Executing script for Modbus Action {self.name} ({self.action_name})")

        try:
            script: ServerScript = cast(ServerScript, frappe.get_doc(
                "Server Script", self.server_script))

            # Set up the context for API script execution
            frappe.form_dict.connection_id = self.connection

            # Convert parameters table to dict
            params = {p.parameter: p.value for p in self.parameters}
            frappe.form_dict.params = params

            # Log parameters for debugging
            logger.debug(f"Script parameters: {params}")

            # Store context in flags for access during execution
            connection_doc = frappe.get_doc(
                "Modbus Connection", str(self.connection))
            frappe.flags.modbus_context = {
                "action": self,
                "connection": connection_doc,
                "params": params
            }

            logger.debug(
                f"Modbus context set with connection {connection_doc.name}")

            if script.script_type == "API":
                logger.debug(f"Executing API script {script.name}")
                result = script.execute_method()

                if not result:
                    logger.error(f"Script {script.name} returned no result")
                    return {
                        "status": "error",
                        "value": None,
                        "error": "Script returned nothing"
                    }

                logger.debug(f"Script execution result: {result}")

                # Ensure we have a proper dictionary with expected keys
                if not isinstance(result, dict):
                    logger.warning(
                        f"Script {script.name} returned non-dict result: {result}")
                    # Convert non-dict result to a standard format
                    return {
                        "status": "success",
                        "value": result,
                        "error": None
                    }

                return {
                    "status": result.get("status", "success"),
                    "value": result.get("value"),
                    "error": result.get("error")
                }
            else:
                logger.debug(
                    f"Executing non-API script {script.name} with event_doc: {event_doc is not None}")
                result = script.execute_doc(event_doc) if event_doc else None
                return {
                    "status": "success" if result is not None else "error",
                    "value": result,
                    "error": "No event document provided" if not event_doc else None
                }
        except Exception as e:
            logger.exception(
                f"Error executing script for Modbus Action {self.name}: {str(e)}")
            return {
                "status": "error",
                "value": None,
                "error": str(e)
            }
        finally:
            logger.debug(f"Clearing modbus context for action {self.name}")
            frappe.flags.modbus_context = None
