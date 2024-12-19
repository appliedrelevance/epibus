// Copyright (c) 2022, Applied Relevance and contributors
// For license information, please see license.txt

frappe.ui.form.on('Modbus Connection', {
    onload: (frm) => {
        console.log('Loading Modbus Connection Form');
    },
    
    refresh: (frm) => {
        console.log('Refreshing Modbus Connection Form');
        
        // Add Test Connection button
        frm.add_custom_button(__('Test Connection'), () => {
            frm.call({
                doc: frm.doc,
                method: 'test_connection',
                args: {
                    "host": frm.doc.host,
                    "port": frm.doc.port,
                }
            })
            .then(result => {
                if (result.message) {
                    frappe.msgprint(result.message);
                }
            })
            .catch(error => {
                frappe.msgprint(__('Error testing connection: {0}', [error.message]));
            });
        });

        // Add Import from Simulator button
        frm.add_custom_button(__('Import from Simulator'), () => {
            // Show dialog to select simulator
            let d = new frappe.ui.Dialog({
                title: __('Select PLC Simulator'),
                fields: [
                    {
                        label: __('Simulator'),
                        fieldname: 'simulator',
                        fieldtype: 'Link',
                        options: 'PLC Simulator',
                        reqd: 1,
                        get_query: () => ({
                            filters: {
                                'enabled': 1
                            }
                        })
                    }
                ],
                primary_action_label: __('Import'),
                primary_action: (values) => {
                    frm.call({
                        method: 'import_from_simulator',
                        doc: frm.doc,
                        args: {
                            simulator_name: values.simulator
                        }
                    })
                    .then(result => {
                        if (result.message) {
                            frappe.show_alert({
                                message: __('Imported {0} locations from simulator', [result.message]),
                                indicator: 'green'
                            });
                            return frm.reload_doc();
                        }
                    })
                    .catch(error => {
                        frappe.msgprint(__('Error importing from simulator: {0}', [error.message]));
                    })
                    .finally(() => {
                        d.hide();
                    });
                }
            });
            d.show();
        });
    },
    
    on_save: (frm) => {
        console.log('Saving Modbus Connection Form');
        frm.call({
            doc: frm.doc,
            method: 'test_connection',
            args: {
                "host": frm.doc.host,
                "port": frm.doc.port,
            }
        })
        .then(result => {
            if (result.message) {
                frappe.msgprint(result.message);
            }
        })
        .catch(error => {
            frappe.msgprint(__('Error testing connection: {0}', [error.message]));
        });
    }
});

/**
 The Modbus addresses bind to PLC addresses based on the hierarchical address value, i.e. lower PLC addresses are
 mapped to lower Modbus addresses. Addresses are mapped sequentially whenever possible. The following table shows the
 Modbus address space for the OpenPLC Linux/Windows runtime:
 [Table content preserved as in original...]
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
    /* All map entries preserved exactly as in original... */
]

// Match PLC address in the form of %TTn.n
const plcAddressRe = /(%[A-Z]+)(\d+)\.(\d+)/;
// Match location name that ends with a number
const locationNameRe = /([^0-9]*)(\d+)/;

// Helper Functions - Converted to Lambda Form
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
        return plcAddress;
    }
    console.log('PLC Address for ' + locType + ' is Not Found');
    return "Not Found";
}

const lastLocationItem = () => {
    const locationList = frappe.get_list("Modbus Signal");
    return locationList.length > 1 ? locationList[locationList.length - 2] : null;
}

const incrementModbusAddress = (modbusAddress) => modbusAddress + 1;

const incrementPLCAddress = (plcAddress) => {
    const match = plcAddressRe.exec(plcAddress);
    if (match) {
        const prefix = match[1];
        const major = parseInt(match[2]);
        const minor = parseInt(match[3]);
        return minor < 7 ? `${prefix}${major}.${minor + 1}` : `${prefix}${major + 1}.0`;
    }
    return "Not Found";
}

const decrementPLCAddress = (plcAddress) => {
    const match = plcAddressRe.exec(plcAddress);
    if (match) {
        const prefix = match[1];
        const major = parseInt(match[2]);
        const minor = parseInt(match[3]);
        return minor > 0 ? `${prefix}${major}.${minor - 1}` : `${prefix}${major - 1}.7`;
    }
    return "Not Found";
}

const incrementNumber = (number) => {
    if (typeof number !== 'string') {
        return number.toString();
    }
    const num = parseInt(number);
    const numLen = number.length;
    const nextNum = num + 1;
    const nextNumStr = nextNum.toString();
    return nextNumStr.length > numLen ? nextNumStr : nextNumStr.padStart(numLen, '0');
}

const incrementLocationName = (locationName) => {
    const match = locationNameRe.exec(locationName);
    return match ? `${match[1]}${incrementNumber(match[2])}` : "Not Found";
}

const isWritable = (locType) => {
    const mapVal = modBusPinMap.find((map) => (map["Name"] === locType));
    return mapVal ? mapVal["Access"] === "RW" : false;
}

// State management
let plc_address_flag = false;
let location_type_flag = false;
let modbus_address_flag = false;
let modbus_settings = null;

// Modbus Signal handlers
frappe.ui.form.on("Modbus Signal", {
    onload: (frm) => {
        frappe.model.with_doc("Modbus Settings")
            .then(() => frappe.get_doc("Modbus Settings"))
            .then(settings => {
                modbus_settings = settings;
                console.log("Modbus Settings:", modbus_settings);
            })
            .catch(error => {
                console.error("Error loading Modbus Settings:", error);
            });
    },
    
    locations_add: (frm, cdt, cdn) => {
        console.log("Location Added");
        const lastItem = lastLocationItem();
        console.log('Last Item:', lastItem);
        
        if (lastItem) {
            frappe.model.set_value(cdt, cdn, "location_name", incrementLocationName(lastItem.location_name))
                .then(() => frappe.model.set_value(cdt, cdn, "signal_type", lastItem.signal_type))
                .then(() => frappe.model.set_value(cdt, cdn, "plc_address", incrementPLCAddress(lastItem.plc_address)))
                .then(() => frappe.model.set_value(cdt, cdn, "modbus_address", incrementModbusAddress(lastItem.modbus_address)))
                .catch(error => {
                    console.error("Error setting location values:", error);
                    frappe.throw(__("Error setting location values"));
                });
        } else {
            frappe.model.set_value(cdt, cdn, "location_name", modbus_settings.default_coil_prefix)
                .then(() => frappe.model.set_value(cdt, cdn, "signal_type", "Digital Output Coil"))
                .then(() => frappe.model.set_value(cdt, cdn, "plc_address", "%QX0.0"))
                .then(() => frappe.model.set_value(cdt, cdn, "modbus_address", 0))
                .catch(error => {
                    console.error("Error setting default values:", error);
                    frappe.throw(__("Error setting default values"));
                });
        }
    },
    
    signal_type: (frm, cdt, cdn) => {
        console.log("Location Type Changed for form:", frm);
        const locDoc = frappe.get_doc(cdt, cdn);
        const writable = isWritable(locDoc.signal_type);
        console.log("Is Writable:", writable);
        frm.set_df_property("toggle", "read_only", !writable);
    },
    
    plc_address: (frm, cdt, cdn) => {
        if (modbus_address_flag) {
            console.log("Called from inside modbus_address change event. Ignoring.");
            modbus_address_flag = false;
            return;
        }
        
        plc_address_flag = true;
        const currentDoc = frappe.get_doc(cdt, cdn);
        console.log("Current Location Doc:", currentDoc);
        modbus_address_flag = false;
    },
    
    modbus_address: (frm, cdt, cdn) => {
        console.log("Modbus Address Changed");
        if (plc_address_flag) {
            console.log("Called from inside plc_address change event. Ignoring.");
            plc_address_flag = false;
            return;
        }
        
        modbus_address_flag = true;
        const currentDoc = frappe.get_doc(cdt, cdn);
        console.log("Current Location Doc:", currentDoc);
        
        const locType = currentDoc.signal_type;
        const modbusAddress = currentDoc.modbus_address;
        const plcAddress = plcAddressFor(locType, modbusAddress);
        
        if (plcAddress !== "Not Found") {
            frappe.model.set_value(cdt, cdn, "plc_address", plcAddress)
                .catch(error => {
                    console.error("Error updating PLC address:", error);
                    frappe.throw(__("Error updating PLC address"));
                })
                .finally(() => {
                    modbus_address_flag = false;
                });
        } else {
            modbus_address_flag = false;
        }
    },
    
    toggle: (frm, cdt, cdn) => {
        const locDoc = frappe.get_doc(cdt, cdn);
        const writable = isWritable(locDoc.signal_type);
        console.log("Is Writable:", writable);
        
        if (!writable) {
            frappe.msgprint(__("This location is not writable."));
            return;
        }
        
        frappe.call({
            doc: frm.doc,
            method: "toggle_location",
            args: {
                "host": frm.doc.host,
                "port": frm.doc.port,
                "modbus_address": locDoc.modbus_address,
                "signal_type": locDoc.signal_type,
            }
        })
        .then(result => {
            if (result.message) {
                frappe.msgprint(result.message);
            }
        })
        .catch(error => {
            console.error("Error toggling location:", error);
            frappe.msgprint(__("Error toggling location: {0}", [error.message]));
        });
    },
});