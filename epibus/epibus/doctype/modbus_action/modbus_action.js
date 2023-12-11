// Function to test the connection
const test_connection = (frm) => {
	frappe.db.get_doc("Modbus Connection", frm.doc.connection)
		.then((connection) => {
			let loc = connection.locations.find(
				(location) => location.name === frm.doc.location
			);
			if (!loc) {
				frappe.msgprint(__("Location not found"));
				return;
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
};

// Function to trigger an action
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

// Event handlers
frappe.ui.form.on("Modbus Action", {
	refresh: function (frm) {
		frm.add_custom_button(__("Trigger Action"), function () {
			return trigger_action(frm);
		});
	},
	location: function (frm) {
		return test_connection(frm); // Assuming you want to test the connection when location changes
	},
	bit_value: function (frm) {
		return test_connection(frm); // Assuming you want to test the connection when bit_value changes
	},
});
