# type: ignore
try:
    # Get parameters from the doc
    docs = frappe.form_dict.get('docs')
    if not docs:
        frappe.throw("No document data provided")

    doc = json.loads(str(docs))
    parameters = doc.get('parameters', [])

    # Extract warehouse parameters
    warehouse_from = None
    warehouse_to = None

    for param in parameters:
        if param.get('parameter') == "warehouse_from":
            warehouse_from = param.get('value')
        elif param.get('parameter') == "warehouse_to":
            warehouse_to = param.get('value')

    if not warehouse_from or not warehouse_to:
        frappe.throw(
            "Both warehouse_from and warehouse_to parameters are required")

    # Get the connection from the doc
    connection = frappe.get_doc("Modbus Connection", doc.get('connection'))
    if not connection:
        frappe.throw("Modbus Connection not found")

    # Get the signals from the connection's child table
    signal_from = None
    signal_to = None

    for signal in connection.signals:
        if signal.signal_name == warehouse_from:
            signal_from = signal
        elif signal.signal_name == warehouse_to:
            signal_to = signal

    if not signal_from:
        frappe.throw(
            f"Signal {warehouse_from} not found in connection {connection.name}")
    if not signal_to:
        frappe.throw(
            f"Signal {warehouse_to} not found in connection {connection.name}")

    # Write TRUE to both signals using the connection
    connection.write_signal(signal_from, True)
    connection.write_signal(signal_to, True)

    # Set success result in frappe.flags
    frappe.flags.status = "success"
    frappe.flags.value = f"Successfully set signals for {warehouse_from} and {warehouse_to}"
    frappe.flags.error = None

except Exception as e:
    frappe.log_error(f"Error in storage_warehouse_to_receiving: {str(e)}")
    frappe.flags.status = "error"
    frappe.flags.value = None
    frappe.flags.error = str(e)
