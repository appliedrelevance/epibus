frappe.ui.form.on("Modbus Connection", {
    refresh: function (frm) {
        // Add test connection button if the form is not new
        if (!frm.is_new()) {
            frm.add_custom_button(__('Test Connection'), function () {
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

        // Update PLC addresses for all signals on load
        if (frm.doc.signals) {
            frm.doc.signals.forEach(signal => {
                update_plc_address(frm, signal.doctype, signal.name);
            });
        }
    }
});

frappe.ui.form.on('Modbus Signal', {
    signal_type: function (frm, cdt, cdn) {
        update_plc_address(frm, cdt, cdn);
    },

    modbus_address: function (frm, cdt, cdn) {
        update_plc_address(frm, cdt, cdn);
    },

    signals_add: function (frm, cdt, cdn) {
        update_plc_address(frm, cdt, cdn);
    }
});

function update_plc_address(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.signal_type && row.modbus_address !== undefined) {
        frm.call({
            doc: row,
            method: 'calculate_plc_address',
            callback: () => {
                console.log('🔄 PLC Address updated for signal:', row.signal_name);
                frm.refresh_field('signals');
            }
        });
    }
}