frappe.ui.form.on('Modbus Action', {
    refresh: function(frm) {
        if (frm.doc.signal) {
            frm.trigger('update_field_visibility');
        }

        // Add test script button for saved docs with test document
        if (!frm.is_new() && frm.doc.test_document) {
            frm.add_custom_button(__('Test Script'), () => {
                frm.call('execute_script')
                    .then(r => {
                        if (r.message) {
                            frappe.show_alert({
                                message: r.message,
                                indicator: 'green'
                            });
                        }
                    });
            }, __('Actions'));
        }
    },

    setup: function(frm) {
        // Filter signals based on selected device
        frm.set_query('signal', function(doc) {
            return {
                filters: {
                    'parent': doc.device
                }
            };
        });
    },

    device: function(frm) {
        // Clear signal when device changes
        frm.set_value('signal', '');
    },

    signal: function(frm) {
        if (!frm.doc.signal) return;
        frm.trigger('update_field_visibility');
    },

    update_field_visibility: function(frm) {
        if (!frm.doc.signal) return;

        frappe.model.with_doc('Modbus Signal', frm.doc.signal, function() {
            const signal = frappe.get_doc('Modbus Signal', frm.doc.signal);
            const isDigital = signal.signal_type.includes('Digital');
            const isInput = signal.signal_type.includes('Input');

            // Toggle value fields
            frm.toggle_display('boolean_value', isDigital);
            frm.toggle_display('float_value', !isDigital);

            // Clear inappropriate values
            if (isDigital) {
                frm.set_value('float_value', null);
            } else {
                frm.set_value('boolean_value', null);
            }

            // Handle action type
            if (isInput && frm.doc.action_type === 'Write') {
                frm.set_value('action_type', 'Read');
            }
            frm.set_df_property('action_type', 'options', 
                isInput ? 'Read' : 'Read\nWrite');
        });
    },

    trigger_doctype: function(frm) {
        // Clear test document when doctype changes
        if (frm.doc.test_document) {
            frm.set_value('test_document', null);
        }
    }
});