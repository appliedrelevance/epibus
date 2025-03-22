# -*- coding: utf-8 -*-
# Copyright (c) 2023, Applied Relevance and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from typing import Dict


@frappe.whitelist(allow_guest=True)
def get_csrf_token() -> Dict[str, str]:
    """Get CSRF token for frontend authentication."""
    csrf_token = frappe.sessions.get_csrf_token()
    frappe.logger().debug(f"Generated CSRF token: {csrf_token}")
    return {"csrf_token": csrf_token}
