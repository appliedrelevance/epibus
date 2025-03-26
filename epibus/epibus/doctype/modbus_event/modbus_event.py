import frappe
from frappe.utils import now
from frappe.model.document import Document
from epibus.epibus.utils.epinomy_logger import get_logger
from epibus.epibus.doctype.modbus_action.modbus_action import ModbusAction
from typing import cast
import traceback

logger = get_logger(__name__)


class ModbusEvent(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        action: DF.Link | None
        connection: DF.Link | None
        error_message: DF.SmallText | None
        event_type: DF.Literal["Read", "Write", "Signal Update", "Connection Test", "Action Execution", "Error"]
        new_value: DF.Data | None
        previous_value: DF.Data | None
        signal: DF.Link | None
        stack_trace: DF.LongText | None
        status: DF.Literal["Success", "Failed"]
        timestamp: DF.Datetime
    # end: auto-generated types

    @staticmethod
    def log_event(event_type, device, status="Success", signal=None, action=None,
                  previous_value=None, new_value=None, error=None, message=None):
        """Create a new Modbus Event log entry

        Args:
            event_type (str): Type of event (Read/Write/etc)
            device (str): Name of Modbus Connection
            status (str, optional): Success/Failed. Defaults to "Success".
            signal (str, optional): Name of Modbus Signal
            action (str, optional): Name of Modbus Action
            previous_value (str, optional): Previous signal value
            new_value (str, optional): New signal value
            error (Exception, optional): Exception if event failed
            message (str, optional): Narrative description of the event
        """
        try:
            event: ModbusEvent = cast(ModbusEvent, frappe.get_doc({
                "doctype": "Modbus Event",
                "event_type": event_type,
                "status": status,
                "device": device,
                "signal": signal,
                "action": action,
                "previous_value": str(previous_value) if previous_value is not None else None,
                "new_value": str(new_value) if new_value is not None else None,
                "timestamp": now(),
                "stack_trace": None,
                "error_message": "",
                "message": message
            }))

            if error:
                event.error_message = str(error)
                event.stack_trace = traceback.format_exc()

            event.insert(ignore_permissions=True)
            logger.debug(
                f"Created Modbus Event: {event.name} - {event_type} on {device}")

        except Exception as e:
            logger.error(f"Failed to create Modbus Event: {str(e)}")
            # Don't raise - we don't want event logging to interrupt operations

    def validate(self):
        """Validate event data"""
        if self.event_type in ["Read", "Write"] and not self.signal:
            frappe.throw("Signal is required for Read/Write events")

        if self.event_type == "Action Execution" and not self.action:
            frappe.throw("Action is required for Action Execution events")

    @frappe.whitelist(methods=['POST'])
    def retry_action(self) -> None:
        """Retry failed action if this was an action execution event"""
        if self.event_type != "Action Execution":
            frappe.throw("Can only retry Action Execution events")

        if not self.action:
            frappe.throw("No action associated with this event")

        action_doc = frappe.get_doc("Modbus Action", str(self.action))
        if not isinstance(action_doc, ModbusAction):
            frappe.throw("The action is not a valid ModbusAction")

        if not hasattr(action_doc, 'execute_script'):
            frappe.throw("The action does not have an execute_script method")
