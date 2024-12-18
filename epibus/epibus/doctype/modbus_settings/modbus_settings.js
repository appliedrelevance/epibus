// Copyright (c) 2024, Applied Relevance and contributors
// For license information, please see license.txt

frappe.ui.form.on('Modbus Settings', {
    refresh: function(frm) {
        // Add simulator control buttons when simulator is enabled
        if (frm.doc.enable_simulator) {
            frm.add_custom_button(__('Start Simulator'), function() {
                startSimulator(frm);
            }, __('Simulator Controls'));

            frm.add_custom_button(__('Stop Simulator'), function() {
                stopSimulator(frm);
            }, __('Simulator Controls'));

            frm.add_custom_button(__('View I/O Monitor'), function() {
                showIOMonitor(frm);
            }, __('Simulator Controls'));
        }

        // Set indicator based on connection status
        updateConnectionIndicator(frm);
    },

    enable_simulator: function(frm) {
        if (frm.doc.enable_simulator) {
            // When simulator is enabled, create simulator connection if it doesn't exist
            frappe.call({
                method: 'epibus.simulator.setup_simulator_connection',
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('Simulator connection created'),
                            indicator: 'green'
                        });
                        frm.refresh();
                    }
                }
            });
        }
    },

    auto_fluctuate_inputs: function(frm) {
        if (frm.doc.auto_fluctuate_inputs && !frm.doc.fluctuation_interval_ms) {
            frm.set_value('fluctuation_interval_ms', 1000);
        }
    }
});

// Function to start the simulator
function startSimulator(frm) {
    frappe.call({
        method: 'epibus.simulator.start_simulator',
        callback: function(r) {
            if (r.message) {
                frm.set_value('connection_status', 'Connected');
                frm.set_value('last_status_update', frappe.datetime.now_datetime());
                
                frappe.show_alert({
                    message: __('Simulator started successfully'),
                    indicator: 'green'
                });

                // Setup WebSocket connection for real-time updates
                setupWebSocket(frm);
            }
        }
    });
}

// Function to stop the simulator
function stopSimulator(frm) {
    frappe.call({
        method: 'epibus.simulator.stop_simulator',
        callback: function(r) {
            if (r.message) {
                frm.set_value('connection_status', 'Disconnected');
                frm.set_value('last_status_update', frappe.datetime.now_datetime());
                
                frappe.show_alert({
                    message: __('Simulator stopped'),
                    indicator: 'orange'
                });

                // Disconnect WebSocket
                if (window.simulatorSocket) {
                    window.simulatorSocket.close();
                }
            }
        }
    });
}

// Function to show I/O monitor dialog
function showIOMonitor(frm) {
    if (frm.doc.connection_status !== 'Connected') {
        frappe.throw(__('Please start the simulator first'));
        return;
    }

    // Create a dialog to show real-time I/O values
    let d = new frappe.ui.Dialog({
        title: __('PLC Simulator I/O Monitor'),
        fields: [
            {
                fieldname: 'io_section',
                fieldtype: 'Section Break',
                label: __('Digital I/O')
            },
            {
                fieldname: 'digital_outputs_html',
                fieldtype: 'HTML'
            },
            {
                fieldname: 'digital_inputs_html',
                fieldtype: 'HTML'
            },
            {
                fieldname: 'register_section',
                fieldtype: 'Section Break',
                label: __('Registers')
            },
            {
                fieldname: 'analog_inputs_html',
                fieldtype: 'HTML'
            },
            {
                fieldname: 'holding_registers_html',
                fieldtype: 'HTML'
            }
        ],
        size: 'extra-large' // makes dialog larger
    });

    // Load initial I/O values
    refreshIOValues(d);

    // Setup periodic refresh
    d.monitor_refresh = setInterval(() => refreshIOValues(d), 1000);

    // Clean up on dialog close
    d.onhide = function() {
        clearInterval(d.monitor_refresh);
    };

    d.show();
}

// Function to refresh I/O values in monitor dialog
function refreshIOValues(dialog) {
    frappe.call({
        method: 'epibus.simulator.get_io_values',
        callback: function(r) {
            if (r.message) {
                updateIODisplay(dialog, r.message);
            }
        }
    });
}

// Function to update I/O display in monitor dialog
function updateIODisplay(dialog, data) {
    // Update Digital Outputs display
    let do_html = `<div class="row">
        ${data.digital_outputs.map((output, idx) => `
            <div class="col-sm-3">
                <label class="switch">
                    <input type="checkbox" ${output.value ? 'checked' : ''} 
                           onchange="toggleOutput(${output.address}, this.checked)">
                    <span class="slider round"></span>
                </label>
                <span class="ml-2">DO ${output.address}</span>
            </div>
        `).join('')}
    </div>`;
    dialog.fields_dict.digital_outputs_html.$wrapper.html(do_html);

    // Update Digital Inputs display
    let di_html = `<div class="row">
        ${data.digital_inputs.map((input, idx) => `
            <div class="col-sm-3">
                <span class="indicator ${input.value ? 'green' : 'gray'}">
                    DI ${input.address}: ${input.value ? 'ON' : 'OFF'}
                </span>
            </div>
        `).join('')}
    </div>`;
    dialog.fields_dict.digital_inputs_html.$wrapper.html(di_html);

    // Similar updates for analog inputs and holding registers...
}

// Function to setup WebSocket connection
function setupWebSocket(frm) {
    frappe.realtime.on('simulator_status_update', function(data) {
        frm.set_value('connection_status', data.status);
        frm.set_value('last_status_update', frappe.datetime.now_datetime());
        
        if (data.status === 'Error') {
            frappe.show_alert({
                message: __('Simulator error: ') + data.message,
                indicator: 'red'
            });
        }
    });

    frappe.realtime.on('simulator_value_update', function(data) {
        // Handle real-time value updates
        // This will be used by the I/O monitor dialog
        if (cur_dialog && cur_dialog.monitor_refresh) {
            updateIODisplay(cur_dialog, data);
        }
    });
}

// Function to update connection indicator
function updateConnectionIndicator(frm) {
    const status_colors = {
        'Connected': 'green',
        'Disconnected': 'gray',
        'Connecting': 'orange',
        'Error': 'red'
    };

    if (frm.doc.connection_status) {
        frm.page.set_indicator(
            frm.doc.connection_status,
            status_colors[frm.doc.connection_status]
        );
    }
}

// Function to toggle digital output
function toggleOutput(address, value) {
    frappe.call({
        method: 'epibus.simulator.set_output',
        args: {
            address: address,
            value: value ? 1 : 0
        },
        callback: function(r) {
            if (!r.exc) {
                frappe.show_alert({
                    message: __(`Output ${address} set to ${value ? 'ON' : 'OFF'}`),
                    indicator: 'green'
                });
            }
        }
    });
}