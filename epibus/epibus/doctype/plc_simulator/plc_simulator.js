// Copyright (c) 2024, Applied Relevance and contributors
// For license information, please see license.txt

frappe.ui.form.on('PLC Simulator', {
    refresh: function(frm) {
        // Add simulator control buttons
        if (frm.doc.enabled) {
            let status = frm.doc.connection_status;
            
            if (status === 'Disconnected' || status === 'Error') {
                frm.add_custom_button(__('Start Simulator'), () => {
                    frm.call('start_simulator')
                        .then(() => frm.refresh());
                });
            } else if (status === 'Connected') {
                frm.add_custom_button(__('Stop Simulator'), () => {
                    frm.call('stop_simulator')
                        .then(() => frm.refresh());
                });

                // Add I/O monitor button
                frm.add_custom_button(__('I/O Monitor'), () => {
                    show_io_monitor(frm);
                });
            }
        }

        // Set indicator based on status
        set_connection_indicator(frm);

        // Setup realtime updates
        setup_realtime_updates(frm);
    },

    enabled: function(frm) {
        if (!frm.doc.enabled) {
            frm.call('stop_simulator')
                .then(() => frm.refresh());
        }
    }
});

function set_connection_indicator(frm) {
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

function setup_realtime_updates(frm) {
    // Remove existing handlers if any
    frappe.realtime.off('simulator_status_update');
    frappe.realtime.off('simulator_value_update');

    // Setup new handlers
    frappe.realtime.on('simulator_status_update', (data) => {
        // Only refresh if this is for our simulator
        if (data.name === frm.doc.name) {
            // Update status without triggering a full reload
            frm.doc.connection_status = data.status;
            frm.doc.last_status_update = frappe.datetime.now_datetime();
            
            // Update the UI
            set_connection_indicator(frm);
            frm.refresh_header();
            
            // Show any error messages
            if (data.status === 'Error' && data.message) {
                frappe.show_alert({
                    message: __('Simulator error: ') + data.message,
                    indicator: 'red'
                });
            }
        }
    });

    frappe.realtime.on('simulator_value_update', (data) => {
        if (cur_dialog && cur_dialog.monitor_interval) {
            refresh_io_points(cur_dialog, frm);
        }
    });
}

function show_io_monitor(frm) {
    let d = new frappe.ui.Dialog({
        title: __('I/O Monitor'),
        fields: [
            {
                fieldname: 'digital_outputs_section',
                fieldtype: 'Section Break',
                label: __('Digital Outputs')
            },
            {
                fieldname: 'digital_outputs_html',
                fieldtype: 'HTML'
            },
            {
                fieldname: 'digital_inputs_section',
                fieldtype: 'Section Break',
                label: __('Digital Inputs')
            },
            {
                fieldname: 'digital_inputs_html',
                fieldtype: 'HTML'
            },
            {
                fieldname: 'analog_section',
                fieldtype: 'Section Break',
                label: __('Analog I/O')
            },
            {
                fieldname: 'analog_html',
                fieldtype: 'HTML'
            }
        ],
        size: 'large'
    });

    // Initial render
    refresh_io_points(d, frm);

    // Setup periodic refresh
    d.monitor_interval = setInterval(() => refresh_io_points(d, frm), 1000);

    // Cleanup on close
    d.onhide = function() {
        clearInterval(d.monitor_interval);
    };

    d.show();
}

function refresh_io_points(dialog, frm) {
    frm.call('get_io_points')
        .then((r) => {
            if (r.message) {
                update_io_display(dialog, organize_io_points(r.message));
            }
            return r;
        })
        .catch((err) => {
            frappe.show_alert({
                message: __('Failed to refresh I/O points'),
                indicator: 'red'
            });
            console.error('Error refreshing I/O points:', err);
        });
}

function organize_io_points(points) {
    return {
        digital_outputs: points.filter(p => p.signal_type.includes('Digital Output')),
        digital_inputs: points.filter(p => p.signal_type.includes('Digital Input')),
        analog_points: points.filter(p => p.signal_type.includes('Analog'))
    };
}

function update_io_display(dialog, points) {
    // Update Digital Outputs
    let do_html = generate_digital_outputs_html(points.digital_outputs);
    dialog.fields_dict.digital_outputs_html.$wrapper.html(do_html);

    // Update Digital Inputs
    let di_html = generate_digital_inputs_html(points.digital_inputs);
    dialog.fields_dict.digital_inputs_html.$wrapper.html(di_html);

    // Update Analog I/O
    let analog_html = generate_analog_html(points.analog_points);
    dialog.fields_dict.analog_html.$wrapper.html(analog_html);
}

function generate_digital_outputs_html(outputs) {
    return `
        <div class="row">
            ${outputs.map(output => `
                <div class="col-sm-3 mb-3">
                    <div class="custom-control custom-switch">
                        <input type="checkbox" class="custom-control-input"
                            id="do_${output.modbus_address}"
                            ${output.value === '1' || output.toggle ? 'checked' : ''}
                            onchange="handle_output_change('${output.modbus_address}', this.checked)">
                        <label class="custom-control-label" for="do_${output.modbus_address}">
                            ${output.location_name} (${output.modbus_address})
                        </label>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function generate_digital_inputs_html(inputs) {
    return `
        <div class="row">
            ${inputs.map(input => `
                <div class="col-sm-3 mb-3">
                    <div class="indicator ${input.value === '1' ? 'green' : 'gray'}">
                        ${input.location_name} (${input.modbus_address})
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function generate_analog_html(points) {
    return `
        <div class="row">
            ${points.map(point => `
                <div class="col-sm-4 mb-3">
                    <div class="analog-point">
                        <label>${point.location_name} (${point.modbus_address})</label>
                        <div class="value-display">
                            ${point.value || '0'}
                            ${generate_analog_controls(point)}
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function generate_analog_controls(point) {
    if (point.signal_type.includes('Output')) {
        return `
            <div class="analog-controls mt-2">
                <input type="range" class="form-control-range"
                    min="0" max="65535" value="${point.value || 0}"
                    onchange="handle_analog_change('${point.modbus_address}', this.value)">
            </div>
        `;
    }
    return '';
}

// Global handlers for HTML events
window.handle_output_change = function(address, value) {
    frappe.call({
        method: 'epibus.simulator.set_output',
        args: {
            address: parseInt(address),
            value: value ? 1 : 0
        }
    }).then((r) => {
        if (r.message) {
            frappe.show_alert({
                message: __(`Output ${address} set to ${value ? 'ON' : 'OFF'}`),
                indicator: 'green'
            });
        }
        return r;
    }).catch((err) => {
        frappe.show_alert({
            message: __('Failed to set output value'),
            indicator: 'red'
        });
        console.error('Error setting output:', err);
    });
};

window.handle_analog_change = function(address, value) {
    frappe.call({
        method: 'epibus.simulator.set_holding_register',
        args: {
            address: parseInt(address),
            value: parseInt(value)
        }
    }).then((r) => {
        if (r.message) {
            frappe.show_alert({
                message: __(`Register ${address} set to ${value}`),
                indicator: 'green'
            });
        }
        return r;
    }).catch((err) => {
        frappe.show_alert({
            message: __('Failed to set register value'),
            indicator: 'red'
        });
        console.error('Error setting register:', err);
    });
};