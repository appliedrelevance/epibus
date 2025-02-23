frappe.ui.form.on('Modbus Signal', {
    refresh: function (frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('Start Monitoring'), function () {
                frappe.call({
                    method: 'epibus.epibus.utils.signal_monitor.start_monitoring',
                    type: 'POST',
                    args: {
                        'signal_id': frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __('Starting signal monitoring...'),
                }).then(r => {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Started monitoring signal'),
                            indicator: 'green'
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Monitoring Error'),
                            message: r.message.message || __('Failed to start monitoring'),
                            indicator: 'red'
                        });
                    }
                });
            }, __('Actions'));
        }
    }
});
