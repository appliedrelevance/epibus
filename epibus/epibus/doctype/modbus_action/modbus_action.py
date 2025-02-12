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
        description: DF.SmallText | None
        device: DF.Link
        enabled: DF.Check
        interval_seconds: DF.Int
        parameters: DF.Table[ModbusParameter]
        server_script: DF.Link
        signal: DF.Link
        trigger_doctype: DF.Link | None
        trigger_event: DF.Literal["Before Insert", "After Insert", "Before Save", "After Save", "Before Submit", "After Submit", "Before Cancel",
                                  "After Cancel", "Before Delete", "After Delete", "Before Save (Submitted Document)", "After Save (Submitted Document)"]
        trigger_type: DF.Literal["API", "DocType Event", "Scheduler Event"]
    # end: auto-generated types

    def validate(self):
        if not self.device:
            frappe.throw(_("Device is required"))

        if not self.signal:
            frappe.throw(_("Signal is required"))

        if not self.server_script:
            frappe.throw(_("Server Script is required"))

            self.validate_script_type()

        script: ServerScript = cast(ServerScript, frappe.get_doc(
            "Server Script", self.server_script))  # type: ignore
        if script.script_type not in ("API"):
            frappe.throw(_("Server Script must be of type API"))

    def validate_script_type(self):
        """Validate the script type of the linked server script"""
        script: ServerScript = cast(ServerScript, frappe.get_doc(
            "Server Script", self.server_script))
        if script.script_type not in ("API"):
            frappe.throw(_("Server Script must be of type API"))

    @frappe.whitelist()
    def execute_script(self, event_doc=None):
        """Execute the linked server script"""
        script: ServerScript = cast(ServerScript, frappe.get_doc(
            "Server Script", self.server_script))

        # Set up the context for API script execution
        frappe.form_dict.device_id = self.device
        frappe.form_dict.signal_id = self.signal

        # Convert parameters table to dict
        params = {p.parameter: p.value for p in self.parameters}
        frappe.form_dict.params = params

        # Store context in flags for access during execution
        frappe.flags.modbus_context = {
            "action": self,
            "signal": frappe.get_doc("Modbus Signal", self.signal),
            "device": frappe.get_doc("Modbus Connection", self.device),
            "params": params
        }

        try:
            if script.script_type == "API":
                result = script.execute_method()
                return {
                    "status": result.get("status", "unknown"),
                    "value": result.get("value"),
                    "error": result.get("error")
                }
            else:
                return script.execute_doc(event_doc) if event_doc else None
        finally:
            frappe.flags.modbus_context = None
