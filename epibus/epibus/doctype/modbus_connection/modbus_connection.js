// Copyright (c) 2024, Applied Relevance and contributors
// For license information, please see license.txt

frappe.ui.form.on("Modbus Connection", {
    refresh: function(frm) {
        // Add test connection button if the form is not new
        if (!frm.is_new()) {
            frm.add_custom_button(__('Test Connection'), function() {
                frm.call({
                    method: 'test_connection',
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: __('Testing Connection...'),
                }).then(r => {
                    frappe.msgprint({
                        title: __('Connection Test Result'),
                        message: r.message,
                        indicator: r.message.includes('successful') ? 'green' : 'red'
                    });
                });
            }, __('Actions'));
        }
    }
});