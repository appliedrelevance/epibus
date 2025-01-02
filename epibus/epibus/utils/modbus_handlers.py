# In epibus/epibus/utils/modbus_handlers.py
import frappe
from epibus.epibus.utils.epinomy_logger import get_logger

logger = get_logger(__name__)

def handle_doc_event(doc, method):
    """Handle document events and execute relevant Modbus Actions
    
    Args:
        doc: The document that triggered the event
        method: The event method name (e.g. 'on_submit', 'validate', etc.)
    """
    try:
        # Find all Modbus Actions configured for this doctype and event
        actions = frappe.get_all(
            "Modbus Action",
            filters={
                "trigger_doctype": doc.doctype,
                f"handle_{method}": 1,
                "docstatus": 1  # Only consider submitted actions
            }
        )
        
        if not actions:
            return
            
        logger.debug(
            f"Found {len(actions)} Modbus Action(s) for {doc.doctype} "
            f"event {method}"
        )
        
        # Execute each matching action
        for action_name in actions:
            try:
                action = frappe.get_doc("Modbus Action", action_name)
                action.execute_script(doc)
            except Exception as e:
                logger.error(
                    f"Error executing Modbus Action {action_name} for "
                    f"{doc.doctype} {doc.name} event {method}: {str(e)}"
                )
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Modbus Action Event Handler Error - {action_name}"
                )
                
    except Exception as e:
        logger.error(
            f"Error handling {method} event for {doc.doctype} {doc.name}: {str(e)}"
        )
        frappe.log_error(
            frappe.get_traceback(),
            "Modbus Action Event Handler Error"
        )