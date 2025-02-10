frappe.ui.form.on('Modbus Action', {
    refresh: function(frm) {
        if (!frm.is_new() && frm.doc.server_script) {
            // Changed executeMethod to always use 'execute_script'
            frm.add_custom_button(__('Test Script'), () => {
                frm.call({
                    method: 'execute_script', // Changed from execute_action to execute_script
                    doc: frm.doc,
                    freeze: true, 
                    freeze_message: __('Executing Script...'),
                }).then(r => {
                    // Rest of the handler code remains the same
                    if (r && r.message) {
                        let indicator, msg;
                        
                        if (typeof r.message === 'object') {
                            if (r.message.status === 'success') {
                                indicator = 'green';
                                msg = `Value: ${r.message.value}`;
                            } else {
                                indicator = 'red';
                                msg = `Error: ${r.message.error || 'Unknown error'}`;
                            }
                        } else {
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

        // Filter server scripts to show appropriate types
        frm.set_query('server_script', function() {
            return {
                filters: {
                    'script_type': ['in', ['DocType Event', 'Scheduler Event', 'API']],
                    'disabled': 0
                }
            };
        });

        // Filter DocTypes to only show those with event hooks
        frm.set_query('trigger_doctype', function() {
            return {
                filters: {
                    'is_submittable': 1,
                    'istable': 0
                }
            };
        });
    },

    trigger_type: function(frm) {
        // Clear irrelevant fields when trigger type changes
        if (frm.doc.trigger_type !== 'DocType Event') {
            frm.set_value('trigger_doctype', '');
            frm.set_value('trigger_event', '');
        }
        if (frm.doc.trigger_type !== 'Scheduler Event') {
            frm.set_value('interval_seconds', '');
        }

        // Update script type filter based on trigger type
        frm.set_query('server_script', function() {
            let script_types = ['API'];
            
            // Add appropriate script types based on trigger type
            if (frm.doc.trigger_type === 'DocType Event') {
                script_types.push('DocType Event');
            } else if (frm.doc.trigger_type === 'Scheduler Event') {
                script_types.push('Scheduler Event');
            }

            return {
                filters: {
                    'script_type': ['in', script_types],
                    'disabled': 0
                }
            };
        });
    },

    device: function(frm) {
        // Clear signal when device changes
        frm.set_value('signal', '');
    }
});