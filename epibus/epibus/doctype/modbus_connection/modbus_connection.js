// Copyright (c) 2022, Applied Relevance and contributors
// For license information, please see license.txt

frappe.ui.form.on('Modbus Connection', {
	refresh: function (frm) {
		console.log('Refreshing Modbus Connection');
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
	"Memory Register(16 bit)": "%MW",
	"Memory Register(32 bit)": "%MD",
	"Memory Register(64 bit)": "%ML",
}

let plc_address_flag = false;
let location_type_flag = false;
let modbus_address_flag = false;

const stopPropagation = (event_name) => {
}

const startPropagation = (event_name) => {
	$(document).on(event_name, stopPropagation);
}

const isPropagationStopped = (event_name) => {

}

frappe.ui.form.on("Modbus Location", {
	location_type: function (frm, cdt, cdn) {
		if (!frappe.get_doc(cdt, cdn).location_type) return;
		let locType = frappe.get_doc(cdt, cdn).location_type;
		frappe.msgprint(`Location Type for ${frm.id} Changed to ${locType}`);
	},
	plc_address: function (frm, cdt, cdn) {
		if (modbus_address_flag) {
			modbus_address_flag = false;
			return;
		}
		plc_address_flag = true;
		if (!frappe.get_doc(cdt, cdn).plc_address) return;
		let plc_address = frappe.get_doc(cdt, cdn).plc_address;
		console.log(plc_address, modbus_address_flag)
		let locType = frappe.get_doc(cdt, cdn).location_type;
		const prefix = portPrefixMap[locType];
		let plcValues = plc_address.substring(prefix.length).split('.');
		let calculatedModbus = (parseInt(plcValues[0]) * 8) + parseInt(plcValues[1]);
		let location_type = calculatedModbus > 799 ? "Digital Output Slave Coil" : "Digital Output Coil";
		frappe.model.set_value(cdt, cdn, "modbus_address", calculatedModbus);
		frappe.model.set_value(cdt, cdn, "location_type", location_type);
		modbus_address_flag = false;
	},
	modbus_address: function (frm, cdt, cdn) {
		if (plc_address_flag) {
			plc_address_flag = false;
			return;
		};
		modbus_address_flag = true;
		if (!frappe.get_doc(cdt, cdn).modbus_address) return;
		let modbus_address = frappe.get_doc(cdt, cdn).modbus_address;
		let location_type = modbus_address > 799 ? "Digital Output Slave Coil" : "Digital Output Coil";
		let plc_address = `%QX${parseInt(modbus_address / 8)}.${modbus_address % 8}`;
		frappe.model.set_value(cdt, cdn, "plc_address", plc_address);
		frappe.model.set_value(cdt, cdn, "location_type", location_type);
		plc_address_flag = false;
	},
	force_true: function (frm, cdt, cdn) {
		frappe.msgprint("Force True");
	},
	force_false: function (frm, cdt, cdn) {
		frappe.msgprint("Force False");
	}
});