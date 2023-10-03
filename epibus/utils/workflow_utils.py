import frappe

def on_workflow_state_change(doc, method):
    # Check if 'workflow_state' field exists
    print("Processing workflow state change")
    if not hasattr(doc, 'workflow_state'):
        print(f"Ignoring workflow state change for {doc.doctype} {doc.name} because 'workflow_state' field is not present")
        return  # exit the function if 'current_state' is not present

    doctype = doc.doctype
    current_state = doc.workflow_state

    # Log the message
    print(f"Workflow state changed for {doctype} {doc.name} to state: {current_state} method: {method}")

    # Lookup relevant Modbus Actions based on trigger_doctype and trigger_state
    modbus_actions = frappe.get_all('Modbus Action',
                                    filters={
                                        'trigger_doctype': doctype,
                                        'trigger_state': current_state
                                    })
    print(f"Found {len(modbus_actions)} Modbus Actions to execute")
    # Execute trigger_action on each matching Modbus Action
    for action in modbus_actions:
        print(f"Executing Modbus Action {action.name}")
        modbus_action_doc = frappe.get_doc('Modbus Action', action.name)
        modbus_action_doc.trigger_action(source_doc=doc)


