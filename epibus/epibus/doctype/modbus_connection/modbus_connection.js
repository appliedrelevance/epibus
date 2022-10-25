// Copyright (c) 2022, Applied Relevance and contributors
// For license information, please see license.txt

frappe.ui.form.on('Modbus Connection', {
	refresh: function (frm) {
		frm.add_custom_button(__('Test Connection'), function () {
			frm.call({
				doc: frm.doc,
				method: 'test_connection',
				args: {
					"host": frm.doc.host,
					"port": frm.doc.port,
				},
				callback: function (r) {
					if (r.message) {
						frappe.msgprint(r.message);
					}
				}
			});
		});
	}
});

const portPrefixMap = {
	"Digital Output Coil": "%QX",
	"Digital Output Slave Coil": "%QX",
	"Digital Input Contact": "%IX",
	"Digital Input Slave Contact": "%IX",
	"Analog Input Register": "%IW",
	"Memory Register (16 bit)": "%MW",
	"Memory Register (32 bit)": "%MD",
	"Memory Register (64 bit)": "%ML",
}

frappe.ui.form.on("Modbus Location", {
	location_type: function (frm, cdt, cdn) {
		if (!frappe.get_doc(cdt, cdn).location_type) return;
		let locType = frappe.get_doc(cdt, cdn).location_type;
		frappe.msgprint(`Location Type for ${frm.id} Changed to ${locType}`);
		// frappe.call({
		// 	method: "erpnext.projects.doctype.timesheet.timesheet.get_activity_cost",
		// 	args: {
		// 		employee: frm.doc.employee,
		// 		activity_type: frm.selected_doc.activity_type,
		// 		currency: frm.doc.currency
		// 	},
		// 	callback: function (r) {
		// 		if (r.message) {
		// 			frappe.model.set_value(cdt, cdn, "billing_rate", r.message["billing_rate"]);
		// 			frappe.model.set_value(cdt, cdn, "costing_rate", r.message["costing_rate"]);
		// 			calculate_billing_costing_amount(frm, cdt, cdn);
		// 		}
		// 	}
		// });
	},
	force_true: function (frm, cdt, cdn) {
		frappe.msgprint("Force True");
	},
	force_false: function (frm, cdt, cdn) {
		frappe.msgprint("Force False");
	}
});
