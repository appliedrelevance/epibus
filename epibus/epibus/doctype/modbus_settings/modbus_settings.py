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

		enable_triggers: DF.Check
		polling_interval: DF.Int
	# end: auto-generated types
	pass
