# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)

class ModbusAction(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        action_name: DF.Data
        action_type: DF.Literal["Read", "Write"]
        boolean_value: DF.Literal["HIGH", "LOW"]
        device: DF.Link
        float_value: DF.Float
        handle_after_insert: DF.Check
        handle_before_insert: DF.Check
        handle_before_save: DF.Check
        handle_before_update_after_submit: DF.Check
        handle_on_cancel: DF.Check
        handle_on_restore: DF.Check
        handle_on_submit: DF.Check
        handle_on_trash: DF.Check
        handle_on_update: DF.Check
        handle_on_update_after_submit: DF.Check
        handle_validate: DF.Check
        monitor_signal: DF.Check
        signal: DF.Link
        signal_type: DF.Data | None
        test_document: DF.DynamicLink | None
        trigger_doctype: DF.Link | None
        trigger_script: DF.Code | None
    # end: auto-generated types

    def validate(self):
        """Validate action configuration"""
        if not self.device:
            frappe.throw(_("Device is required"))
            
        if not self.signal:
            frappe.throw(_("Signal is required"))
            
        # Get the signal doc to validate value types
        signal = frappe.get_doc("Modbus Signal", self.signal)
        
        # Validate values based on signal type
        if "Digital" in signal.signal_type:
            if self.float_value:
                frappe.throw(_("Cannot set analog value for digital signal"))
        else:  # Analog signal
            if self.boolean_value:
                frappe.throw(_("Cannot set digital value for analog signal"))

        # Validate event handling
        if not any([
            self.monitor_signal, 
            self.handle_validate,
            self.handle_before_insert,
            self.handle_after_insert,
            self.handle_before_save,
            self.handle_before_update_after_submit,
            self.handle_on_update_after_submit,
            self.handle_on_update,
            self.handle_on_restore,
            self.handle_on_submit,
            self.handle_on_cancel,
            self.handle_on_trash
        ]):
            frappe.throw(_("At least one event or signal monitoring must be enabled"))
            
        # Validate that we have a trigger doctype if any events are enabled
        if any([
            self.handle_validate,
            self.handle_before_insert,
            self.handle_after_insert,
            self.handle_before_save,
            self.handle_before_update_after_submit,
            self.handle_on_update_after_submit,
            self.handle_on_update,
            self.handle_on_restore,
            self.handle_on_submit,
            self.handle_on_cancel,
            self.handle_on_trash
        ]) and not self.trigger_doctype:
            frappe.throw(_("Trigger DocType is required when events are enabled"))

    def handle_signal_change(self, old_value, new_value):
        """Handle signal value changes"""
        try:
            # Create a simple context object to represent the signal change
            signal_event = frappe._dict({
                'event_type': 'signal_change',
                'signal': self.signal,
                'old_value': old_value,
                'new_value': new_value
            })
            self.execute_script(signal_event)
        except Exception as e:
            logger.error(f"Error handling signal change for {self.name}: {str(e)}")
            frappe.log_error(frappe.get_traceback(), 
                           f"Modbus Action Signal Handler Error - {self.name}")

    @frappe.whitelist()
    def execute_script(self, event_doc=None):
        """Execute the trigger script
        
        Args:
            event_doc: Either a Document for document events or
                    a dict for signal change events with event_type='signal_change'
        """
        if not self.trigger_script:
            return
            
        try:
            # If no event doc provided, try to use test document
            if event_doc is None and self.test_document:
                event_doc = frappe.get_doc(self.trigger_doctype, self.test_document)
            elif event_doc is None:
                frappe.throw(_("No event document provided for testing"))

            # Setup context for script execution
            context = {
                "doc": self,  # The Modbus Action doc
                "signal": frappe.get_doc("Modbus Signal", self.signal),
                "target": event_doc,  # The document that triggered the event
                "event_doc": event_doc,  # Alias for target for compatibility
                "logger": logger,
                "frappe": frappe._dict(
                    # Only expose safe operations
                    get_doc=frappe.get_doc,
                    new_doc=frappe.new_doc,
                    get_list=frappe.get_list,
                    get_all=frappe.get_all,
                    get_value=frappe.db.get_value,  # Note: from db
                    get_single_value=frappe.db.get_single_value,  # Note: from db
                    get_meta=frappe.get_meta,
                    get_cached_doc=frappe.get_cached_doc,
                    log_error=frappe.log_error,
                    get_traceback=frappe.get_traceback,
                    msgprint=frappe.msgprint,
                    throw=frappe.throw,
                    _=frappe._,
                    scrub=frappe.scrub,
                    db=frappe._dict(
                        get_value=frappe.db.get_value,
                        get_list=frappe.db.get_list,
                        get_all=frappe.db.get_all, 
                        exists=frappe.db.exists,
                        escape=frappe.db.escape,
                        sql=frappe.db.sql,
                        get_single_value=frappe.db.get_single_value
                    )
                ),
            }
            
            # Execute the script with restricted context
            frappe.utils.safe_exec.safe_exec(
                self.trigger_script,
                _globals=context,
                _locals=None,
                restrict_commit_rollback=True
            )
            return _("Script executed successfully")
            
        except Exception as e:
            error_msg = f"Error executing script for {self.name}: {str(e)}"
            logger.error(error_msg)
            frappe.log_error(frappe.get_traceback(), "Modbus Action Script Error")
            raise