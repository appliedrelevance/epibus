# Copyright (c) 2025, Applied Relevance and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.core.doctype.server_script.server_script import ServerScript
from frappe import _
from typing import cast

import logging
from epibus.epibus.utils.epinomy_logger import get_logger
logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)


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
        doctype_event: DF.Literal["Before Insert", "After Insert", "Before Save", "After Save", "Before Submit", "After Submit", "Before Cancel",
                                  "After Cancel", "Before Delete", "After Delete", "Before Save (Submitted Document)", "After Save (Submitted Document)"]
        enabled: DF.Check
        event_frequency: DF.Literal["All", "Hourly", "Daily", "Weekly", "Monthly",
                                    "Yearly", "Hourly Long", "Daily Long", "Weekly Long", "Monthly Long", "Cron"]
        modbus_signal: DF.Link
        parameters: DF.Table[ModbusParameter]
        reference_doctype: DF.Link | None
        script_type: DF.Literal["DocType Event",
                                "Scheduler Event", "Signal Change", "API"]
        server_script: DF.Link
        signal_condition: DF.Literal["Any Change",
                                     "Equals", "Greater Than", "Less Than"]
        signal_value: DF.Data | None
    # end: auto-generated types

    def validate(self):
        if not self.connection:
            frappe.throw(_("Modbus Connection is required"))

        if not self.server_script:
            frappe.throw(_("Server Script is required"))

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

                return result
            else:
                logger.debug(
                    f"Executing non-API script {script.name} with event_doc: {event_doc is not None}")
                result = script.execute_doc(event_doc) if event_doc else None
                return result
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


@frappe.whitelist(methods=['GET', 'POST'])
def test_action_script(action_name):
    """
    Execute the server script for a Modbus Action
    
    Args:
        action_name (str): The name of the Modbus Action document
        
    Returns:
        dict: Result of script execution
    """
    logger.info(f"Testing script for Modbus Action: {action_name}")
    
    try:
        # Get the Modbus Action document
        action_doc = frappe.get_doc("Modbus Action", action_name)

        # Skip all signal checks and directly execute the script
        logger.info(f"Directly executing server script: {action_doc.server_script}")
        
        # Execute the script
        result = action_doc.execute_script()
        logger.info(f"Script execution result: {result}")
        return result
    
    except Exception as e:
        logger.exception(f"Error testing script for Modbus Action {action_name}: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_signals_for_connection(doctype, txt, searchfield, start, page_len, filters):
    """
    Custom query to fetch signals for a connection with formatted display names
    """
    logger.debug(
        f"🔍 Getting signals for connection: {filters.get('connection')}")

    # Query for signals matching the parent (connection)
    signals = frappe.get_all(
        "Modbus Signal",
        filters={
            "parent": filters.get("connection"),
            "signal_name": ["like", f"%{txt}%"]
        },
        fields=["name", "signal_name", "signal_type", "modbus_address"],
        limit_start=start,
        limit_page_length=page_len
    )

    # Format the results for display in the dropdown
    formatted_signals = []
    for signal in signals:
        # Format: "SIGNAL_NAME (TYPE) - Address: XXX"
        display_name = f"{signal.signal_name} ({signal.signal_type}) - Address: {signal.modbus_address}"
        formatted_signals.append([signal.name, display_name])

    logger.debug(f"📊 Found {len(formatted_signals)} signals")
    return formatted_signals


@frappe.whitelist()
def check_recent_events(action_name, signal_name):
    """
    Check if there are recent Modbus Events for a specific action and signal

    Args:
        action_name (str): The name of the Modbus Action
        signal_name (str): The name of the signal that was changed

    Returns:
        dict: Result with found status and event info
    """
    logger.debug(
        f"🔍 Checking recent events for action: {action_name}, signal: {signal_name}")

    try:
        # Get the action document for reference
        action_doc = frappe.get_doc("Modbus Action", action_name)

        # Look for recent Modbus Events related to this action's execution
        # Searching for events in the last 15 seconds
        from frappe.utils import add_to_date, now_datetime

        events = frappe.get_all(
            "Modbus Event",
            filters={
                "creation": [">=", add_to_date(now_datetime(), seconds=-15)],
                "event_type": "Script Execution",
                "action": action_name
            },
            fields=["name", "creation", "event_type",
                    "signal", "action"],
            order_by="creation desc"
        )

        if events:
            logger.info(
                f"✅ Found {len(events)} recent events for {action_name}")
            # Format the event information for display
            event_info = "<ul>"
            for event in events[:3]:  # Show max 3 recent events
                event_info += f"<li>Event {event.name}: Signal {event.signal}, Value: {event.value}</li>"
            event_info += "</ul>"

            return {
                "found": True,
                "event_info": event_info,
                "event_count": len(events)
            }
        else:
            logger.warning(f"⚠️ No recent events found for {action_name}")
            return {
                "found": False,
                "event_info": "No events found in the last 15 seconds"
            }

    except Exception as e:
        logger.error(f"❌ Error checking recent events: {str(e)}")
        return {
            "found": False,
            "error": str(e)
        }


@frappe.whitelist()
def test_doctype_event(self):
    """
    Test a DocType Event script without actually triggering document changes

    Args:
        self: The Modbus Action document

    Returns:
        dict: Test result
    """
    logger.debug(f"🧪 Testing DocType Event script for {self.name}")

    try:
        # Get the referenced server script
        script = frappe.get_doc("Server Script", self.server_script)

        # Create a dummy doc for the referenced doctype
        # This won't be saved/submitted, just used for script execution context
        dummy_doc = frappe.new_doc(self.reference_doctype)

        # Add some minimal test data
        dummy_doc.update({
            "_test_mode": True,
            "doctype": self.reference_doctype,
            "name": f"Test-{frappe.utils.now()}"
        })

        # Set up the modbus context
        connection_doc = frappe.get_doc("Modbus Connection", self.connection)
        signal_doc = None
        if self.modbus_signal:
            # Find the signal in the connection's signals table
            for signal in connection_doc.signals:
                if signal.name == self.modbus_signal:
                    signal_doc = signal
                    break

        # Create params dict from parameters table
        params = {p.parameter: p.value for p in self.parameters}

        # Store context in flags for access during execution
        frappe.flags.modbus_context = {
            "action": self,
            "connection": connection_doc,
            "signal": signal_doc,
            "device": connection_doc,  # For backward compatibility
            "params": params,
            "test_mode": True,
            "event_type": self.doctype_event,
            "dummy_doc": dummy_doc
        }

        logger.debug(
            f"🧩 Set up test context with connection {connection_doc.name}")

        try:
            # Execute the script with the dummy doc
            result = script.execute_doc(dummy_doc)

            # Create a Modbus Event to record this test
            frappe.get_doc({
                "doctype": "Modbus Event",
                "event_type": "Script Execution",
                "reference_doctype": "Modbus Action",
                "reference_name": self.name,
                "signal": self.modbus_signal or "N/A",
                "value": "Test DocType Event",
                "details": f"Test execution of {self.doctype_event} event on {self.reference_doctype}",
                "message": f"Test execution of action '{self.name}' for {self.doctype_event} event on {self.reference_doctype}"
            }).insert(ignore_permissions=True)

            return {
                "status": "success",
                "value": f"Test execution successful. DocType Event: {self.doctype_event}",
                "result": result
            }

        except Exception as e:
            logger.error(f"❌ Error executing script: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            # Clear context
            frappe.flags.modbus_context = None

    except Exception as e:
        logger.error(f"❌ Error in test setup: {str(e)}")
        return {
            "status": "error",
            "error": f"Test setup failed: {str(e)}"
        }


@frappe.whitelist()
def direct_test_script(action_name):
    """
    Directly execute the server script for a Modbus Action without any signal checks
    
    Args:
        action_name (str): The name of the Modbus Action document
        
    Returns:
        dict: Result of script execution
    """
    logger.info(f"Direct test of script for Modbus Action: {action_name}")
    
    try:
        # Get the Modbus Action document
        action_doc = frappe.get_doc("Modbus Action", action_name)
        
        # Get the connection document
        connection_doc = frappe.get_doc("Modbus Connection", action_doc.connection)
        
        # Set up the context for script execution
        frappe.flags.modbus_context = {
            "action": action_doc,
            "connection": connection_doc,
            "params": {p.parameter: p.value for p in action_doc.parameters},
            "test_mode": True
        }
        
        # Get the server script
        script_doc = frappe.get_doc("Server Script", action_doc.server_script)
        
        # Execute the script
        logger.info(f"Executing server script: {script_doc.name}")
        result = script_doc.execute_method()
        logger.info(f"Script execution result: {result}")
        
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        logger.exception(f"Error in direct test of script: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        # Clear the context
        frappe.flags.modbus_context = None


@frappe.whitelist()
def test_scheduler_event(self):
    """
    Test a Scheduler Event script by simulating a scheduled run

    Args:
        self: The Modbus Action document

    Returns:
        dict: Test result
    """
    logger.debug(f"🧪 Testing Scheduler Event script for {self.name}")

    try:
        # Get the referenced server script
        script = frappe.get_doc("Server Script", self.server_script)

        # Set up the modbus context
        connection_doc = frappe.get_doc("Modbus Connection", self.connection)
        signal_doc = None
        if self.modbus_signal:
            # Find the signal in the connection's signals table
            for signal in connection_doc.signals:
                if signal.name == self.modbus_signal:
                    signal_doc = signal
                    break

        # Create params dict from parameters table
        params = {p.parameter: p.value for p in self.parameters}

        # Store context in flags for access during execution
        frappe.flags.modbus_context = {
            "action": self,
            "connection": connection_doc,
            "signal": signal_doc,
            "device": connection_doc,  # For backward compatibility
            "params": params,
            "test_mode": True,
            "event_type": "scheduler"
        }

        logger.debug(
            f"🧩 Set up test context with connection {connection_doc.name}")

        try:
            # Execute the script without any arguments (as scheduler would)
            result = script.execute_method()

            # Create a Modbus Event to record this test
            frappe.get_doc({
                "doctype": "Modbus Event",
                "event_type": "Script Execution",
                "reference_doctype": "Modbus Action",
                "reference_name": self.name,
                "signal": self.modbus_signal or "N/A",
                "value": "Test Scheduler Event",
                "details": f"Test execution of {self.event_frequency} scheduler event",
                "message": f"Test execution of scheduler action '{self.name}' with frequency {self.event_frequency}"
            }).insert(ignore_permissions=True)

            return {
                "status": "success",
                "value": f"Test execution successful. Scheduler Event: {self.event_frequency}",
                "result": result
            }

        except Exception as e:
            logger.error(f"❌ Error executing script: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            # Clear context
            frappe.flags.modbus_context = None

    except Exception as e:
        logger.error(f"❌ Error in test setup: {str(e)}")
        return {
            "status": "error",
            "error": f"Test setup failed: {str(e)}"
        }
