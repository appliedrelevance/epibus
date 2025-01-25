# Copyright (c) 2023, Applied Relevance and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class ModbusSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		default_coil_prefix: DF.Data | None
		default_contact_prefix: DF.Data | None
		default_register_prefix: DF.Data | None
		enable_triggers: DF.Check
	# end: auto-generated types
	pass
