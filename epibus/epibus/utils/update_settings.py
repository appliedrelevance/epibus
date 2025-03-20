import frappe

def update_polling_interval(interval=300):
    """Update the polling interval in Modbus Settings."""
    try:
        # Get the Modbus Settings document
        settings = frappe.get_single("Modbus Settings")
        
        # Print current value
        print(f"Current polling interval: {settings.polling_interval}")
        
        # Update the polling interval
        settings.polling_interval = interval
        
        # Save with ignore_permissions
        settings.save(ignore_permissions=True)
        
        # Commit the transaction
        frappe.db.commit()
        
        # Verify the update
        updated_settings = frappe.get_single("Modbus Settings")
        print(f"Updated polling interval: {updated_settings.polling_interval}")
        
        return True
    except Exception as e:
        print(f"Error updating polling interval: {str(e)}")
        return False