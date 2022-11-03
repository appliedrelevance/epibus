// Copyright (c) 2022, Applied Relevance and contributors
// For license information, please see license.txt


const test_connection = (frm) => {
	frappe.db.get_doc("Modbus Connection", frm.doc.connection)
		.then(connection => {
			let loc = connection.locations.find(location => location.name === parseInt(frm.doc.location));
			if (!loc) {
				return frappe.msgprint('Location not found');
			}
			let locint = parseInt(loc.modbus_address);
			let bitvalue = frm.doc.bit_value ? 1 : 0;
			frm.call({
				doc: frm.doc,
				method: 'test_action',
				args: {
					"host": connection.host,
					"port": connection.port,
					"action": frm.doc.action,
					"location": locint,
					"bit_value": bitvalue
				},
				callback: function (r) {
					if (r.message) {
						frappe.msgprint(r.message);
					}
				}
			});
		});
}

frappe.ui.form.on('Modbus Action', {
	refresh: function (frm) {
		frm.add_custom_button(__('Test Connection'), function () {
			console.log('Called Test Connection button handler')
			return test_connection(frm);
		});
	},
	location: function (frm) {
		return test_connection(frm);
	},
	bit_value: function (frm) {
		return test_connection(frm);
	}
});
