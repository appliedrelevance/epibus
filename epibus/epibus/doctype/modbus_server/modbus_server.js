// Copyright (c) 2024, Applied Relevance and contributors
// For license information, please see license.txt

frappe.ui.form.on('Modbus Server', {
    refresh(frm) {
        frm.add_custom_button(__('Start Server'), function () {
            // Call start_server method
            frappe.call({
                method: 'start_server',
                doc: frm.doc,
                args: {
                    hostname: frm.doc.hostname,
                    ports: frm.doc.modbus_port
                },
                callback: function (r) {
                    if (!r.exc) {
                        frm.set_value('status', 'Running');
                        frm.refresh_field('status');
                    }
                }
            });
        });

        frm.add_custom_button(__('Stop Server'), function () {
            // Call stop_server method
            frappe.call({
                method: 'stop_server',
                doc: frm.doc,
                callback: function (r) {
                    if (!r.exc) {
                        frm.set_value('status', 'Stopped');
                        frm.refresh_field('status');
                    }
                }
            });
        });
    }
});
