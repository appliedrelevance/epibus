// Copyright (c) 2022, Applied Relevance and contributors
// For license information, please see license.txt

frappe.ui.form.on('Modbus Connection', {
	onload: function (frm) {
		console.log('Loading Modbus Connection Form');
	},
	refresh: function (frm) {
		console.log('Refreshing Modbus Connection Form');
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
	},
	on_save: function (frm) {
		console.log('Saving Modbus Connection Form');
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

// Match PLC address in the form of %TTn.n
const plcAddressRe = /(%[A-Z]+)(\d+)\.(\d+)/;
// Match location name that ends with a number
const locationNameRe = /([^0-9]*)(\d+)/;

const prefixFor = (locType) => {
	const mapVal = modBusPinMap.find((map) => (map["Name"] === locType));
	const prefix = mapVal ? mapVal["PLC Prefix"] : "Not Found";
	console.log('Prefix for ' + locType + ' is ' + prefix);
	return prefix;
}

const plcAddressFor = (locType, modbusAddress) => {
	const mapVal = modBusPinMap.find((map) => (map["Name"] === locType));
	if (mapVal) {
		const prefix = prefixFor(locType);
		const plcMajor = mapVal["PLC Lower Bound Major"] + Math.floor(modbusAddress / 8);
		const plcMinor = mapVal["PLC Lower Bound Minor"] + (modbusAddress % 8);
		const plcAddress = `${prefix}${plcMajor}.${plcMinor}`;
		console.log('PLC Address for ' + locType + ' is ' + plcAddress);
	} else {
		console.log('PLC Address for ' + locType + ' is Not Found');
		return "Not Found";
	}
}

// Get the list of all locations and return the penultimate one.
const lastLocationItem = () => {
	const locationList = frappe.get_list("Modbus Location");
	if (locationList.length > 1) {
		return locationList[locationList.length - 2];
	}
	else {
		return null;
	}
}

const incrementModbusAddress = (modbusAddress) => {
	return modbusAddress + 1;
}

const incrementPLCAddress = (plcAddress) => {
	const match = plcAddressRe.exec(plcAddress);
	if (match) {
		const prefix = match[1];
		const major = parseInt(match[2]);
		const minor = parseInt(match[3]);
		if (minor < 7) {
			return `${prefix}${major}.${minor + 1}`;
		} else {
			return `${prefix}${major + 1}.0`;
		}
	} else {
		return "Not Found";
	}
}

const decrementPLCAddress = (plcAddress) => {
	const match = plcAddressRe.exec(plcAddress);
	if (match) {
		const prefix = match[1];
		const major = parseInt(match[2]);
		const minor = parseInt(match[3]);
		if (minor > 0) {
			return `${prefix}${major}.${minor - 1}`;
		} else {
			return `${prefix}${major - 1}.7`;
		}
	} else {
		return "Not Found";
	}
}

// Given a string of digits, return the next number padded with leading zeros
// to the length of the original string.
const incrementNumber = (number) => {
	if (typeof number !== 'string') {
		return number.toString();
	}
	const num = parseInt(number);
	const numLen = number.length;
	const nextNum = num + 1;
	const nextNumStr = nextNum.toString();
	const nextNumLen = nextNumStr.length;
	if (nextNumLen > numLen) {
		return nextNumStr;
	} else {
		return nextNumStr.padStart(numLen, '0');
	}
}

const incrementLocationName = (locationName) => {
	const match = locationNameRe.exec(locationName);
	if (match) {
		const prefix = match[1];
		const suffix = incrementNumber(match[2]);
		return `${prefix}${suffix}`;
	} else {
		return "Not Found";
	}
}

const isWritable = (locType) => {
	const mapVal = modBusPinMap.find((map) => (map["Name"] === locType));
	return mapVal ? mapVal["Access"] === "RW" : false;
}


let plc_address_flag = false;
let location_type_flag = false;
let modbus_address_flag = false;
let modbus_settings = null;

frappe.ui.form.on("Modbus Location", {
	onload: function (frm) {
		frappe.model.with_doc("Modbus Settings", function () {
			modbus_settings = frappe.get_doc("Modbus Settings");
			console.log("Modbus Settings: ", settings);
			// Do something with the settings document
		});
	},
	locations_add: function (frm, cdt, cdn) {
		console.log("Location Added");
		const lastItem = lastLocationItem();
		console.log('Last Item: ', lastItem);
		if (lastItem) {
			frappe.model.set_value(cdt, cdn, "location_name", incrementLocationName(lastItem.location_name));
			frappe.model.set_value(cdt, cdn, "location_type", lastItem.location_type);
			frappe.model.set_value(cdt, cdn, "plc_address", incrementPLCAddress(lastItem.plc_address));
			frappe.model.set_value(cdt, cdn, "modbus_address", incrementModbusAddress(lastItem.modbus_address));
		} else {
			frappe.model.set_value(cdt, cdn, "location_name", modbus_settings.default_coil_prefix);
			frappe.model.set_value(cdt, cdn, "location_type", "Digital Output Coil");
			frappe.model.set_value(cdt, cdn, "plc_address", "%QX0.0");
			frappe.model.set_value(cdt, cdn, "modbus_address", 0);
		}
	},
	location_type: function (frm, cdt, cdn) {
		console.log("Location Type Changed for form:", frm);
		const locDoc = frappe.get_doc(cdt, cdn);
		const writable = isWritable(locDoc.location_type);
		console.log("Is Writable: ", writable);
		// Disable toggle button if it is not writable.
		if (!writable) {
			frm.set_df_property("toggle", "read_only", 1);
		} else {
			frm.set_df_property("toggle", "read_only", 0);
		}
	},
	plc_address: function (frm, cdt, cdn) {
		// if modbus_address_flag is set, then this event was triggered by the modbus_address change.
		console.log("PLC Address Changed");
		if (modbus_address_flag) {
			console.log("Called from inside modbus_address change event. Ignoring.");
			modbus_address_flag = false;
			return;
		}
		plc_address_flag = true;
		const currentDoc = frappe.get_doc(cdt, cdn);
		console.log("Current Location Doc: ", currentDoc);
		modbus_address_flag = false;
	},
	modbus_address: function (frm, cdt, cdn) {
		console.log("Modbus Address Changed");
		// If plc_address_flag is set, then this event was triggered by plc_address change.
		if (plc_address_flag) {
			console.log("Called from inside plc_address change event. Ignoring.");
			plc_address_flag = false;
			return;
		};
		modbus_address_flag = true;
		const currentDoc = frappe.get_doc(cdt, cdn);
		console.log("Current Location Doc: ", currentDoc);
		// Compute the PLC Address from the modbus address and update the doc.
		const locType = currentDoc.location_type;
		const modbusAddress = currentDoc.modbus_address;
		const plcAddress = plcAddressFor(locType, modbusAddress);
		currentDoc.plc_address = plcAddress;
		frappe.model.set_value(cdt, cdn, "plc_address", plcAddress);
		plc_address_flag = false;
	},
	toggle: function (frm, cdt, cdn) {
		// If the Location Type has "W" access, then the toggle button should be enabled.
		const locDoc = frappe.get_doc(cdt, cdn);
		const writable = isWritable(locDoc.location_type);
		console.log("Is Writable: ", writable);
		// If location is not writable, notify the user and return.
		if (!writable) {
			frappe.msgprint("This location is not writable.");
			return;
		} else {
			// If the location is writable, call the server toggle function.
			frappe.call({
				doc: frm.doc,
				method: "toggle_location",
				args: {
					"host": frm.doc.host,
					"port": frm.doc.port,
					"modbus_address": locDoc.modbus_address,
					"location_type": locDoc.location_type,
				},
				callback: function (r) {
					if (r.message) {
						frappe.msgprint(r.message);
					}
				}
			});
		}
	},
});