import frappe
from pprint import pprint


def validate(doc, method):
    if doc.doctype == "Pick List":
        for location in doc.locations:
            whse = frappe.get_doc("Warehouse", location.warehouse)
            pprint(whse.as_dict())
            if whse.modbus_action:
                # Call the Modbus Action
                maction = frappe.get_doc(
                    "Modbus Action", whse.modbus_action)
                res = maction.trigger_action()
                frappe.msgprint(res)
            else:
                print("No Modbus Action for this warehouse")
