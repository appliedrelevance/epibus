"""EpiBus Stock Movement Generic Trigger Script

This script can be triggered in two ways:
1. Through a Stock Entry document event (Before Submit)
2. Through ModbusAction.execute_script() method

Context (available from frappe.flags.modbus_context):
- doc: The ModbusAction document
- signal: The Modbus Signal document being controlled
- device: The Modbus Device document
- target: The source document that triggered the event (if any)
- params: Dictionary of parameters from the Modbus Action
- logger: The epinomy logger instance
"""
try:
    # Get our context from what modbus_action.py provides
    modbus_context = frappe.flags.modbus_context
    logger = modbus_context.logger
    logger.info("Started Trigger Modbus Signal")
    target_warehouse = modbus_context['params'].get('Warehouse')
    
    if not target_warehouse:
        frappe.throw("Warehouse parameter is required")
            
    # Process if we have a target document and it's submitted
    has_target = bool(modbus_context['target'] and 
                     hasattr(modbus_context['target'], 'docstatus') and 
                     modbus_context['target'].docstatus == 1)
    
    if has_target:
        # Find items from target warehouse
        warehouse_items = [
            item for item in modbus_context['target'].items 
            if item.s_warehouse == target_warehouse
        ]
        
        if warehouse_items:
            # Attempt to toggle signal
            try:
                modbus_context['signal'].toggle_location_pin()
                frappe.msgprint(
                    f"Successfully toggled signal {modbus_context['signal'].name}",
                    indicator='green'
                )
            except Exception as signal_error:
                frappe.throw(f"Error toggling signal: {str(signal_error)}")
            
            # Add audit comment to target document
            comment_text = (
                f"Modbus Action {modbus_context['doc'].name} triggered:\n"
                f"- Signal: {modbus_context['signal'].name}\n"
                f"- Device: {modbus_context['device'].name}\n"
                f"- Value: HIGH\n"
                f"- Items from {target_warehouse}: "
                f"{', '.join(i.item_code for i in warehouse_items)}"
            )
            
            try:
                modbus_context['target'].add_comment('Comment', text=comment_text)
                modbus_context['target'].save(ignore_permissions=True)
            except Exception as comment_error:
                frappe.throw(f"Error adding comment: {str(comment_error)}")
        else:
            frappe.msgprint(
                f"No items found from warehouse {target_warehouse}",
                indicator='orange'
            )
    else:
        # No target document or not submitted - this is probably a test run
        try:
            modbus_context['signal'].toggle_location_pin()
            frappe.msgprint(
                f"Test successful: Toggled signal {modbus_context['signal'].name}",
                indicator='green'
            )
        except Exception as e:
            frappe.throw(f"Error in test mode: {str(e)}")

except Exception as e:
    frappe.throw(f"Error in Modbus Signal Trigger: {str(e)}")