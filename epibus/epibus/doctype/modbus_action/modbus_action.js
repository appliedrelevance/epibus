// Copyright (c) 2023, Applied Relevance and contributors
// For license information, please see license.txt

frappe.ui.form.on('Modbus Action', {
    refresh: function(frm) {
        setTimeout(() => {
            if (frm.fields_dict['parameters'] && frm.fields_dict['parameters'].grid) {
                let field = frm.fields_dict['parameters'].grid.get_field('field_name');
                if (field && field.df) {
                    field.df.get_options = function() {
                        return new Promise(resolve => {
                            frappe.call({
                                method: 'epibus.epibus.doctype.modbus_action.modbus_action.get_fields',
                                args: {
                                    doctype: frm.doc.trigger_doctype
                                },
                                callback: function(r) {
                                    if (r.message) {
                                        resolve(r.message);
                                    }
                                }
                            });
                        });
                    };
                }
            }
        }, 1000); // adjust the time as needed
    }
});




