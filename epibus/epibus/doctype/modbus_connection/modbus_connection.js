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

/**
 The Modbus addresses bind to PLC addresses based on the hierarchical address value, i.e. lower PLC addresses are
 mapped to lower Modbus addresses. Addresses are mapped sequentially whenever possible. The following table shows the
 Modbus address space for the OpenPLC Linux/Windows runtime:
 Modbus Data Type		Usage					PLC Address			Modbus Data Address	Data Size	Range			Access
 Discrete Output 		Coils Digital Outputs	%QX0.0 – %QX99.7	0 – 799				1 bit		0 or 1			RW
 Discrete Output 		Coils Slave Outputs		%QX100.0 – %QX199.7	800 – 1599			1 bit		0 or 1			RW
 Discrete Input 		Contacts Digital Inputs	%IX0.0 – %IX99.7	0 – 799				1 bit		0 or 1			R
 Discrete Input 		Contacts Slave Inputs	%IX100.0 – %IX199.7	800 – 1599			1 bit		0 or 1			RW
 Analog Input 			Registers Analog Input 	%IW0 – %IW1023		0 – 1023			16 bits		0 – 65535		R
 Holding Registers		Analog Outputs			%QW0 – %QW1023		0 – 1023			16 bits		0 – 65535		RW
 Holding Registers		Memory (16-bits)		%MW0 – %MW1023		1024 – 2048			16 bits		0 – 65535		RW
 Holding Registers		Memory (32-bits)		%MD0 – %MD1023		2048 – 4095			32 bits		0 – 4294967295	RW
 Holding Registers		Memory (64-bits)		%ML0 – %ML1023		4096 – 8191			64 bits		0 – N			RW

  */

const modBusOptions = [
	"Digital Output Coil",
	"Digital Output Slave Coil",
	"Digital Input Contact",
	"Digital Input Slave Contact",
	"Analog Input Register",
	"Analog Output Holding Register",
	"Memory Register (16 bit)",
	"Memory Register (32 bit)",
	"Memory Register (64 bit)",
]

const modBusPinMap = [
	{
		"Data Type": "Discrete Output",
		"Usage": "Coils Digital Outputs",
		"Name": "Digital Output Coil",
		"PLC Prefix": "%QX",
		"PLC Lower Bound Major": 0,
		"PLC Lower Bound Minor": 0,
		"PLC Upper Bound Major": 799,
		"PLC Upper Bound Minor": 7,
		"Modbus Base Address": 0,
		"Data Size": 1,
		"Lower Range": 0,
		"Upper Range": 1,
		"Access": "RW"
	},
	{
		"Data Type": "Discrete Output",
		"Usage": "Coils Slave Outputs",
		"Name": "Digital Output Slave Coil",
		"PLC Prefix": "%QX",
		"PLC Lower Bound Major": 100,
		"PLC Lower Bound Minor": 0,
		"PLC Upper Bound Major": 199,
		"PLC Upper Bound Minor": 7,
		"Modbus Base Address": 800,
		"Data Size": 1,
		"Lower Range": 0,
		"Upper Range": 1,
		"Access": "RW"
	},
	{
		"Data Type": "Discrete Input",
		"Usage": "Contacts Digital Inputs",
		"Name": "Digital Input Contact",
		"PLC Prefix": "%IX",
		"PLC Lower Bound Major": 0,
		"PLC Lower Bound Minor": 0,
		"PLC Upper Bound Major": 799,
		"PLC Upper Bound Minor": 7,
		"Modbus Base Address": 0,
		"Data Size": 1,
		"Lower Range": 0,
		"Upper Range": 1,
		"Access": "R"
	},
	{
		"Data Type": "Discrete Input",
		"Usage": "Contacts Slave Inputs",
		"Name": "Digital Input Slave Contact",
		"PLC Prefix": "%IX",
		"PLC Lower Bound Major": 100,
		"PLC Lower Bound Minor": 0,
		"PLC Upper Bound Major": 199,
		"PLC Upper Bound Minor": 7,
		"Modbus Base Address": 800,
		"Data Size": 1,
		"Lower Range": 0,
		"Upper Range": 1,
		"Access": "RW"
	},
	{
		"Data Type": "Analog Input",
		"Usage": "Registers Analog Input",
		"Name": "Analog Input Register",
		"PLC Prefix": "%IW",
		"PLC Lower Bound Major": 0,
		"PLC Lower Bound Minor": 0,
		"PLC Upper Bound Major": 1023,
		"PLC Upper Bound Minor": 0,
		"Modbus Base Address": 0,
		"Data Size": 16,
		"Lower Range": 0,
		"Upper Range": 65535,
		"Access": "R"
	},
	{
		"Data Type": "Holding Registers",
		"Usage": "Analog Outputs",
		"Name": "Analog Output Holding Register",
		"PLC Prefix": "%QW",
		"PLC Lower Bound Major": 0,
		"PLC Lower Bound Minor": 0,
		"PLC Upper Bound Major": 1023,
		"PLC Upper Bound Minor": 0,
		"Modbus Base Address": 0,
		"Data Size": 16,
		"Lower Range": 0,
		"Upper Range": 65535,
		"Access": "RW"
	},
	{
		"Data Type": "Holding Registers",
		"Usage": "Memory (16-bits)",
		"Name": "Memory Register (16 bit)",
		"PLC Prefix": "%MW",
		"PLC Lower Bound Major": 0,
		"PLC Lower Bound Minor": 0,
		"PLC Upper Bound Major": 1023,
		"PLC Upper Bound Minor": 0,
		"Modbus Base Address": 1024,
		"Data Size": 16,
		"Lower Range": 0,
		"Upper Range": 65535,
		"Access": "RW"
	},
	{
		"Data Type": "Holding Registers",
		"Usage": "Memory (32-bits)",
		"Name": "Memory Register (32 bit)",
		"PLC Prefix": "%MD",
		"PLC Lower Bound Major": 0,
		"PLC Lower Bound Minor": 0,
		"PLC Upper Bound Major": 1023,
		"PLC Upper Bound Minor": 0,
		"Modbus Base Address": 2048,
		"Data Size": 32,
		"Lower Range": 0,
		"Upper Range": 4294967295,
		"Access": "RW"
	},
	{
		"Data Type": "Holding Registers",
		"Usage": "Memory (64-bits)",
		"Name": "Memory Register (64 bit)",
		"PLC Prefix": "%ML",
		"PLC Lower Bound Major": 0,
		"PLC Lower Bound Minor": 0,
		"PLC Upper Bound Major": 1023,
		"PLC Upper Bound Minor": 0,
		"Modbus Base Address": 4096,
		"Data Size": 64,
		"Lower Range": 0,
		"Upper Range": Number.MAX_SAFE_INTEGER,
		"Access": "RW"
	}
]

const prefixFor = (locType) => {
	console.log('Looking for locType ', locType, ' in ', modBusPinMap);
	const mapVal = modBusPinMap.find((map) => (map["Name"] === locType));
	console.log("MapVal: ", mapVal);
	return mapVal ? mapVal["PLC Prefix"] : "Not Found"
}

const plcAddressFor = (locType, modbusAddress) => {
	const mapVal = modBusPinMap.find((map) => (map["Name"] === locType));
	if (mapVal) {
		const prefix = mapVal["PLC Prefix"];
		const plcMajor = mapVal["PLC Lower Bound Major"] + Math.floor(modbusAddress / 8);
		const plcMinor = mapVal["PLC Lower Bound Minor"] + (modbusAddress % 8);
		return `${prefix}${plcMajor}.${plcMinor}`;
	} else {
		return "Not Found";
	}
}


let plc_address_flag = false;
let location_type_flag = false;
let modbus_address_flag = false;

frappe.ui.form.on("Modbus Location", {
	location_type: function (frm, cdt, cdn) {
		console.log("Location Type Changed");
		const locDoc = frappe.get_doc(cdt, cdn);
		const locType = locDoc.location_type;
		if (!locType) return;
		const prefix = prefixFor(locType);
		frappe.msgprint(`Location Type for ${JSON.stringify(locDoc)} Changed to ${locType} with prefix ${prefix}`);
	},
	plc_address: function (frm, cdt, cdn) {
		// if modbus_address_flag is set, then this event was triggered by the modbus_address change.
		console.log("PLC Address Changed");
		if (modbus_address_flag) {
			modbus_address_flag = false;
			return;
		}
		plc_address_flag = true;
		if (!frappe.get_doc(cdt, cdn).plc_address) return;
		let locType = frappe.get_doc(cdt, cdn).location_type;
		let calculatedPlcAddress = plcAddressFor(locType, frappe.get_doc(cdt, cdn).modbusAddress);
		frappe.model.set_value(cdt, cdn, "plc_address", calculatedPlcAddress);
		modbus_address_flag = false;
	},
	modbus_address: function (frm, cdt, cdn) {
		console.log("Modbus Address Changed");
		// If plc_address_flag is set, then this event was triggered by plc_address change.
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
	toggle: function (frm, cdt, cdn) {
		frappe.msgprint("Toggle");
	},
});