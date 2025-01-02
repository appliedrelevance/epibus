# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)

EVENT_FIELDS = [
    'handle_validate', 'handle_before_insert', 'handle_after_insert', 
    'handle_before_save', 'handle_before_update_after_submit',
    'handle_on_update_after_submit', 'handle_on_update', 'handle_on_restore',
    'handle_on_submit', 'handle_on_cancel', 'handle_on_trash'
]

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
    def on_trash(self):
        """Clean up event handlers when document is deleted"""
        try:
            # Clean up document event handlers
            if self.trigger_doctype:
                doctype = frappe.get_doc("DocType", self.trigger_doctype)
                
                # Remove handlers for each event
                for event_field in EVENT_FIELDS:
                    if getattr(self, event_field):
                        event_name = event_field.replace('handle_', '')
                        doctype.remove_handler(event_name, self.name)
                        logger.debug(f"Removed {event_name} handler for {self.name}")

            # Clean up signal monitoring
            if self.monitor_signal:
                try:
                    signal = frappe.get_doc("Modbus Signal", self.signal)
                    signal.remove_handler('value_change', self.name)
                    logger.debug(f"Removed signal monitor for {self.name}")
                except Exception as e:
                    logger.warning(
                        f"Could not remove signal handler for {self.name}: {str(e)}"
                    )

            logger.info(f"Cleaned up event handlers for {self.name}")

        except Exception as e:
            logger.error(f"Error cleaning up handlers for {self.name}: {str(e)}")
            # Don't re-raise - we want deletion to proceed even if cleanup fails

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
        if not any([self.monitor_signal] + [getattr(self, event) for event in EVENT_FIELDS]):
            frappe.throw(_("At least one event or signal monitoring must be enabled"))

    def after_insert(self):
        """Setup event handlers after creation"""
        self.setup_handlers()

    def on_update(self):
        """Update event handlers if configuration changes"""
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup event handlers for monitored events"""
        # Setup document event handlers if doctype specified
        if self.trigger_doctype:
            doctype = frappe.get_doc("DocType", self.trigger_doctype)
            
            # Setup handlers for each enabled event
            for event_field in EVENT_FIELDS:
                if getattr(self, event_field):
                    # Convert handle_on_submit to on_submit etc.
                    event_name = event_field.replace('handle_', '')
                    handler = self.create_handler(event_name)
                    doctype.on_change(event_name, handler, self.name)  # Include handler ID
                    logger.debug(f"Setup {event_name} handler for {self.name}")

        # Setup signal monitoring if enabled
        if self.monitor_signal:
            signal = frappe.get_doc("Modbus Signal", self.signal)
            signal.on_change('value_change', self.handle_signal_change, self.name)  # Include handler ID
            logger.debug(f"Setup signal monitor for {self.name} on {signal.name}")
                
        logger.info(f"Setup event handlers for {self.name}")

    def create_handler(self, event):
        """Create an event handler function for document events"""
        def handler(target_doc):
            try:
                self.execute_script(target_doc)
            except Exception as e:
                logger.error(f"Error in {event} handler for {self.name}: {str(e)}")
                frappe.log_error(frappe.get_traceback(), 
                               f"Modbus Action Handler Error - {self.name}")
        return handler

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
                "event": event_doc,  # Either a document or signal change event
                "logger": logger
            }
            
            # Execute the script
            frappe.safe_eval(self.trigger_script, None, context)
            return _("Script executed successfully")
            
        except Exception as e:
            error_msg = f"Error executing script for {self.name}: {str(e)}"
            logger.error(error_msg)
            frappe.log_error(frappe.get_traceback(), "Modbus Action Script Error")
            raise