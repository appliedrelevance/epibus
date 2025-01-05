// In modbus_action.js

frappe.ui.form.on('Modbus Action', {
    refresh: function(frm) {
        if (!frm.is_new() && frm.doc.server_script) {
            frm.add_custom_button(__('Test Script'), () => {
                frm.call({
                    method: "execute_script",
                    doc: frm.doc,
                    freeze: true, 
                    freeze_message: __('Executing Script...'),
                }).then(r => {
                    // Handle the response more carefully
                    if (r && r.message) {
                        let indicator, msg;
                        
                        // Convert response to string if it's not already
                        if (typeof r.message === 'object') {
                            if (r.message.status === 'success') {
                                indicator = 'green';
                                msg = `Value: ${r.message.value}`;
                            } else {
                                indicator = 'red';
                                msg = `Error: ${r.message.error || 'Unknown error'}`;
                            }
                        } else {
                            // Handle string response
                            indicator = 'blue';
                            msg = r.message;
                        }

                        frappe.msgprint({
                            title: __('Script Execution Result'),
                            message: msg,
                            indicator: indicator
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Script Execution Result'),
                            message: __('No response from script'),
                            indicator: 'orange'
                        });
                    }
                }).catch(err => {
                    // Improved error handling
                    const errorMsg = err.message || err.toString() || 'Unknown error occurred';
                    frappe.msgprint({
                        title: __('Script Execution Failed'),
                        message: errorMsg,
                        indicator: 'red'
                    });
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

        // Update script filter to include API type
        frm.set_query('server_script', function() {
            return {
                filters: {
                    'script_type': ['in', ['DocType Event', 'Scheduler Event', 'API']],
                    'disabled': 0
                }
            };
        });
    }
});