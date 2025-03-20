import frappe
from frappe.commands.utils import pass_context
import click

@click.command('update-polling-interval')
@click.option('--interval', default=300, help='New polling interval in milliseconds')
@pass_context
def update_polling_interval(context, interval=300):
    """Update the polling interval in Modbus Settings."""
    site = context.sites[0]
    frappe.init(site=site)
    frappe.connect()
    
    try:
        # Get the Modbus Settings document
        doc = frappe.get_doc('Modbus Settings')
        
        # Print the current polling interval
        print(f"Current polling interval: {doc.polling_interval}")
        
        # Update the polling interval
        doc.polling_interval = interval
        
        # Save the document with ignore_permissions=True
        doc.save(ignore_permissions=True)
        
        # Commit the transaction
        frappe.db.commit()
        
        # Print the updated polling interval
        print(f"Updated polling interval to: {doc.polling_interval}")
        
    except Exception as e:
        print(f"Error updating polling interval: {str(e)}")
    
    finally:
        frappe.destroy()

commands = [
    update_polling_interval
]