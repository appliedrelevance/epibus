#!/usr/bin/env python3

import frappe
from datetime import date
from erpnext.setup.setup_wizard.setup_wizard import setup_complete

@frappe.whitelist()
def complete_erpnext_setup():
    """Complete ERPNext setup wizard programmatically"""
    
    # Check if setup is already complete
    if frappe.db.get_single_value("System Settings", "setup_complete"):
        frappe.logger().info("Setup already completed")
        return {"status": "already_complete", "message": "Setup already completed"}
    
    frappe.logger().info("Running ERPNext setup wizard...")
    
    # Calculate fiscal year dates (current year)
    current_year = date.today().year
    fy_start_date = f"{current_year}-01-01"
    fy_end_date = f"{current_year}-12-31"
    
    # Setup wizard arguments
    setup_args = {
        'language': 'en',
        'country': 'United States',
        'timezone': 'America/New_York', 
        'currency': 'USD',
        'company_name': 'Roots Intralogistics',
        'company_abbr': 'RL',
        'email': 'admin@rootseducation.co',
        'first_name': 'Administrator',
        'last_name': 'User',
        'fy_start_date': fy_start_date,
        'fy_end_date': fy_end_date,
        'chart_of_accounts': 'Standard',
        'domain': 'Manufacturing'
    }
    
    try:
        # Complete setup wizard
        setup_complete(setup_args)
        frappe.db.commit()
        
        frappe.logger().info("Setup wizard completed successfully")
        return {"status": "success", "message": "Setup wizard completed successfully"}
        
    except Exception as e:
        frappe.logger().error(f"Setup wizard failed: {str(e)}")
        frappe.db.rollback()
        return {"status": "error", "message": f"Setup wizard failed: {str(e)}"}