# -*- coding: utf-8 -*-
# Copyright (c) 2023, Applied Relevance and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import os
import json

no_cache = 1

def get_context(context):
    """
    Prepare the context for the PLC Monitor page.
    Ensures the page has access to the current user's session.
    """
    # Set up page context
    context.no_cache = 1
    context.no_breadcrumbs = 1
    context.no_header = 1
    context.no_footer = 1

    # Ensure user is logged in
    if frappe.session.user == 'Guest':
        frappe.throw(
            _("Please login to access the PLC Monitor"), frappe.PermissionError)

    # Add user info to context for debugging
    context.user = frappe.session.user

    # Ensure CSRF token is available in the session
    if not frappe.session.csrf_token:
        frappe.session.csrf_token = frappe.generate_hash()

    # Add CSRF token to context
    context.csrf_token = frappe.session.csrf_token

    return context