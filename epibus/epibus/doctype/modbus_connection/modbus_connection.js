// Copyright (c) 2022, Applied Relevance and contributors
// For license information, please see license.txt

frappe.ui.form.on('Modbus Connection', {
	refresh: function(frm) {
		frm.add_custom_button(__('Test Connection'), function() {
			frm.call({
				doc: frm.doc,
				method: 'test_connection',
				args: {
					"host": frm.doc.host,
					"port": frm.doc.port,
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint(r.message);
					}
				}
			});
		});
	}
});
