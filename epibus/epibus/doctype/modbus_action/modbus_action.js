frappe.ui.form.on('Modbus Action', {
    refresh: function(frm) {
        // Add formatter for modbus_signal field to show signal_name instead of ID
        frm.fields_dict['modbus_signal'].get_query = function(doc) {
            if (!doc.connection) {
                frappe.msgprint('Please select a Modbus Connection first');
                return {
                    filters: {
                        'name': ''
                    }
                };
            }
            return {
                query: 'epibus.epibus.doctype.modbus_action.modbus_action.get_signals_for_connection',
                filters: {
                    'connection': doc.connection
                }
            };
        };
        
        // Format the display value for modbus_signal
        if (frm.doc.modbus_signal && frm.doc.connection) {
            // Instead of using client.get_value, fetch the parent document
            // which includes all child records
            frappe.model.with_doc('Modbus Connection', frm.doc.connection, function() {
                const conn_doc = frappe.get_doc('Modbus Connection', frm.doc.connection);
                
                // Find the matching signal in the child table
                if (conn_doc && conn_doc.signals) {
                    const signal = conn_doc.signals.find(s => s.name === frm.doc.modbus_signal);
                    
                    if (signal) {
                        // Update the display value
                        frm.fields_dict['modbus_signal'].set_formatted_input(
                            `${signal.signal_name} (${signal.signal_type}) - Address: ${signal.modbus_address}`
                        );
                        console.log(`🔍 Formatted signal display: ${signal.signal_name}`);
                    } else {
                        console.log(`⚠️ Signal ${frm.doc.modbus_signal} not found in connection ${frm.doc.connection}`);
                    }
                }
            });
        }

        // Add Test Script button with enhanced testing based on script type
        if (!frm.is_new() && frm.doc.server_script) {
            frm.add_custom_button(__('Test Script'), () => {
                testScript(frm);
            }, __('Actions'));
        }
    },

    setup: function(frm) {
        // Filter queries for other fields - we're handling modbus_signal in refresh
        
        // Filter server scripts based on type (removed API-only requirement)
        frm.set_query('server_script', function() {
            return {
                filters: {
                    'script_type': ['in', ['DocType Event', 'Scheduler Event', 'API']],
                    'disabled': 0
                }
            };
        });

        // Filter DocTypes to only show those with event hooks
        frm.set_query('reference_doctype', function() {
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
        if (frm.doc.script_type !== 'DocType Event') {
            frm.set_value('reference_doctype', '');
            frm.set_value('doctype_event', '');
        }
        if (frm.doc.script_type !== 'Scheduler Event') {
            frm.set_value('event_frequency', '');
        }

        // Update script type filter based on trigger type
        frm.set_query('server_script', function() {
            // Allow all script types (DocType Event, Scheduler Event, API)
            // This allows for better flexibility when selecting scripts
            return {
                filters: {
                    'script_type': ['in', ['DocType Event', 'Scheduler Event', 'API']],
                    'disabled': 0
                }
            };
        });
    },

    server_script: function(frm) {
        if (!frm.doc.server_script) return;
        
        // Fetch the Server Script details to sync trigger settings
        frappe.db.get_doc('Server Script', frm.doc.server_script)
            .then(script_doc => {
                console.log(`📄 Fetched Server Script: ${script_doc.name}, Type: ${script_doc.script_type}`);
                
                // Sync script_type from Server Script to Modbus Action
                if (script_doc.script_type !== frm.doc.script_type) {
                    frm.set_value('script_type', script_doc.script_type);
                    console.log(`🔄 Updated script_type to: ${script_doc.script_type}`);
                }
                
                // Sync DocType Event settings if applicable
                if (script_doc.script_type === 'DocType Event') {
                    if (script_doc.reference_doctype !== frm.doc.reference_doctype) {
                        frm.set_value('reference_doctype', script_doc.reference_doctype);
                        console.log(`🔄 Updated reference_doctype to: ${script_doc.reference_doctype}`);
                    }
                    
                    if (script_doc.doctype_event !== frm.doc.doctype_event) {
                        frm.set_value('doctype_event', script_doc.doctype_event);
                        console.log(`🔄 Updated doctype_event to: ${script_doc.doctype_event}`);
                    }
                }
                
                // Sync Scheduler Event settings if applicable
                if (script_doc.script_type === 'Scheduler Event') {
                    if (script_doc.event_frequency !== frm.doc.event_frequency) {
                        frm.set_value('event_frequency', script_doc.event_frequency);
                        console.log(`🔄 Updated event_frequency to: ${script_doc.event_frequency}`);
                    }
                    
                    if (script_doc.cron_format !== frm.doc.cron_format) {
                        frm.set_value('cron_format', script_doc.cron_format);
                        console.log(`🔄 Updated cron_format to: ${script_doc.cron_format}`);
                    }
                }
            })
            .catch(err => {
                console.error(`❌ Error fetching Server Script: ${err}`);
            });
    },

    connection: function(frm) {
        // Clear signal when connection changes
        frm.set_value('modbus_signal', '');
        
        // Log for debugging
        console.log('🔄 Connection changed to:', frm.doc.connection);
    }
});

// Function to handle testing of scripts based on their type
function testScript(frm) {
    if (!frm.doc.server_script) {
        frappe.msgprint({
            title: __('Error'),
            message: __('Please select a Server Script first'),
            indicator: 'red'
        });
        return;
    }

    console.log(`🧪 Testing script ${frm.doc.server_script} of type ${frm.doc.script_type}`);
    
    if (frm.doc.script_type === 'Signal Change') {
        testSignalChangeScript(frm);
    } else if (frm.doc.script_type === 'DocType Event') {
        testDocTypeEventScript(frm);
    } else if (frm.doc.script_type === 'Scheduler Event') {
        testSchedulerEventScript(frm);
    } else {
        // Default to direct execution for API scripts
        executeScriptDirectly(frm);
    }
}

// Test Signal Change script by triggering a write to the signal
function testSignalChangeScript(frm) {
    if (!frm.doc.server_script) {
        frappe.msgprint({
            title: __('Error'),
            message: __('Server Script is required for testing'),
            indicator: 'red'
        });
        return;
    }

    console.log(`🧪 Testing script for Modbus Action: ${frm.doc.name}`);
    
    // Show a loading message
    frappe.show_alert({
        message: __(`Testing script for ${frm.doc.action_name}...`),
        indicator: 'blue'
    });
    
    // Call our new endpoint to test the script using promises
    frappe
        .call({
            method: 'epibus.epibus.doctype.modbus_action.modbus_action.test_action_script',
            args: {
                action_name: frm.doc.name
            },
            freeze: true,
            freeze_message: __('Testing Script...')
        })
        .then((r) => {
            const result = r.message;
            if (result.status === 'error') {
                // Handle error from the script execution
                console.error(`❌ Script execution error: ${result.error}`);
                frappe.msgprint({
                    title: __('Script Execution Failed'),
                    message: __(`${result.error}`),
                    indicator: 'red'
                });
                return;
            }

            // Success case
            console.log(`✅ Script executed successfully: ${JSON.stringify(result)}`);
            frappe.msgprint({
                title: __('Script Execution Successful'),
                message: __(`Result: ${JSON.stringify(result)}`),
                indicator: 'green'
            });

        })
        .catch((err) => {
            console.error(`❌ Error during frappe call: ${err}`);
            frappe.msgprint({
                title: __('Script Test Failed'),
                message: __(`An error occurred during the frappe call: ${err}`),
                indicator: 'red'
            });
        });
}

// Test DocType Event script by simulating the event
function testDocTypeEventScript(frm) {
    if (!frm.doc.reference_doctype || !frm.doc.doctype_event) {
        frappe.msgprint({
            title: __('Error'),
            message: __('Reference DocType and DocType Event are required'),
            indicator: 'red'
        });
        return;
    }
    
    frappe.confirm(
        __(`This will simulate a <strong>${frm.doc.doctype_event}</strong> event on <strong>${frm.doc.reference_doctype}</strong>. No actual document will be modified. Continue?`),
        () => {
            // Execute with simulation parameters using promises
            frm.call({
                method: 'test_doctype_event',
                doc: frm.doc,
                freeze: true,
                freeze_message: __('Simulating DocType Event...')
            })
            .then(handleTestResponse)
            .catch(err => {
                console.error(`❌ Error during DocType Event simulation: ${err}`);
                frappe.msgprint({
                    title: __('DocType Event Test Failed'),
                    message: __(`An error occurred: ${err}`),
                    indicator: 'red'
                });
            });
        }
    );
}

// Test Scheduler Event script by simulating the event
function testSchedulerEventScript(frm) {
    if (!frm.doc.event_frequency) {
        frappe.msgprint({
            title: __('Error'),
            message: __('Event Frequency is required'),
            indicator: 'red'
        });
        return;
    }
    
    frappe.confirm(
        __(`This will simulate a <strong>${frm.doc.event_frequency}</strong> scheduler event. Continue?`),
        () => {
            // Execute with simulation parameters using promises
            frm.call({
                method: 'test_scheduler_event',
                doc: frm.doc,
                freeze: true,
                freeze_message: __('Simulating Scheduler Event...')
            })
            .then(handleTestResponse)
            .catch(err => {
                console.error(`❌ Error during Scheduler Event simulation: ${err}`);
                frappe.msgprint({
                    title: __('Scheduler Event Test Failed'),
                    message: __(`An error occurred: ${err}`),
                    indicator: 'red'
                });
            });
        }
    );
}

// Execute API script directly
function executeScriptDirectly(frm) {
    frm.call({
        method: 'execute_script',
        doc: frm.doc,
        freeze: true, 
        freeze_message: __('Executing Script...')
    })
    .then(handleTestResponse)
    .catch(err => {
        console.error(`❌ Error during script execution: ${err}`);
        frappe.msgprint({
            title: __('Script Execution Failed'),
            message: __(`An error occurred: ${err}`),
            indicator: 'red'
        });
    });
}

// Check the event log for script execution evidence
function checkEventLog(frm, signalName) {
    frappe.call({
        method: 'epibus.epibus.doctype.modbus_action.modbus_action.check_recent_events',
        args: {
            action_name: frm.doc.name,
            signal_name: signalName
        }
    })
    .then((r) => {
        if (r.message) {
            if (r.message.found) {
                frappe.msgprint({
                    title: __('Signal Change Test Result'),
                    message: __(`✅ Success! The script was executed when the signal changed.
                            <br><br>Event Log: ${r.message.event_info}`),
                    indicator: 'green'
                });
            } else {
                frappe.msgprint({
                    title: __('Signal Change Test Result'),
                    message: __(`⚠️ The signal was changed successfully, but no script execution was detected.`),
                    indicator: 'orange'
                });
            }
        } else {
            frappe.msgprint({
                title: __('Signal Change Test Result'),
                message: __('⚠️ Could not verify script execution. Please check server logs.'),
                indicator: 'orange'
            });
        }
    })
    .catch(err => {
        console.error(`❌ Error during checkEventLog: ${err}`);
        frappe.msgprint({
            title: __('Error'),
            message: __(`An error occurred: ${err}`),
            indicator: 'red'
        });
    });
}

// Handle the test response 
function handleTestResponse(r) {
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
}