// Copyright (c) 2022, Applied Relevance and contributors
// For license information, please see license.txt

const test_connection = (frm) => {
	frappe.db
		.get_doc("Modbus Connection", frm.doc.connection)
		.then((connection) => {
			let loc = connection.locations.find(
				(location) => location.name === frm.doc.location
			);
			if (!loc) {
				frappe.throw("Location not found");
			}
			let locint = parseInt(loc.modbus_address);
			let bitvalue = frm.doc.bit_value ? 1 : 0;
			frm.call({
				doc: frm.doc,
				method: "test_action",
				args: {
					host: connection.host,
					port: connection.port,
					action: frm.doc.action,
					location: locint,
					bit_value: bitvalue,
				},
				callback: function (r) {
					if (r.message) {
						frappe.show_alert({ message: r.message, indicator: "green" });
					}
				},
			});
		});
	const trigger_action = (frm) => {
		frm.call({
			doc: frm.doc,
			method: "trigger_action",
			callback: function (r) {
				if (r.message) {
					frappe.show_alert({ message: r.message, indicator: "green" });
				}
			},
		});
	};

	frappe.ui.form.on("Modbus Action", {
		refresh: function (frm) {
			frm.add_custom_button(__("Trigger Action"), function () {
				return trigger_action(frm);
			});
		},
		location: function (frm) {
			return trigger_action(frm);
		},
		bit_value: function (frm) {
			return trigger_action(frm);
		},
	});
};
