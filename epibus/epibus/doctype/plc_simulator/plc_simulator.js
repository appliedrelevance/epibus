// Copyright (c) 2024, Applied Relevance and contributors
// For license information, please see license.txt

frappe.ui.form.on('PLC Simulator', {
    refresh: function(frm) {
        frm.doc.io_points = frm.doc.io_points || [];
        
        // Create a dropdown for simulator controls in the menu
        frm.page.clear_menu();
        frm.page.add_menu_item(__('Simulator Controls'), () => {
            setup_simulator_controls(frm);
        });
        
        // Update status and setup event handlers
        update_port_status(frm);
        setup_realtime_updates(frm);
        
        // Set initial control state
        setup_simulator_controls(frm);
    },
    
    enabled: function(frm) {
        if (!frm.doc.enabled) {
            handle_simulator_stop(frm);
        }
    },
    
    before_save: function(frm) {
        frm.doc.io_points = frm.doc.io_points || [];
    },
    
    onhide: function(frm) {
        cleanup_realtime_handlers();
    }
});

// Core simulator control functions
function setup_simulator_controls(frm) {
    frm.page.clear_inner_toolbar();
    
    if (!frm.doc.enabled) {
        return;
    }

    const is_connected = frm.doc.connection_status === 'Connected';
    if (is_connected) {
        frm.page.add_inner_button(__('Stop Simulator'), () => handle_simulator_stop(frm), 'Simulator Controls');
        
        if (frm.doc.io_points?.length > 0) {
            frm.page.add_inner_button(__('I/O Monitor'), () => show_io_monitor(frm), 'Simulator Controls');
        }
    } else {
        frm.page.add_inner_button(__('Start Simulator'), () => handle_simulator_start(frm), 'Simulator Controls');
    }
}

function handle_simulator_start(frm) {
    frm.call('start_simulator')
        .then(r => {
            if (r.message) {
                frappe.show_alert({
                    message: __('Simulator started successfully'),
                    indicator: 'green'
                });
                return frm.reload_doc();
            }
        })
        .then(() => {
            setup_simulator_controls(frm);
        })
        .catch(err => {
            console.error('Error starting simulator:', err);
            frappe.show_alert({
                message: __('Failed to start simulator: ') + err.message,
                indicator: 'red'
            });
        });
}

function handle_simulator_stop(frm) {
    frm.call('stop_simulator')
        .then(r => {
            if (r.message) {
                frappe.show_alert({
                    message: __('Simulator stopped successfully'),
                    indicator: 'yellow'
                });
                return frm.reload_doc();
            }
        })
        .then(() => {
            setup_simulator_controls(frm);
        })
        .catch(err => {
            console.error('Error stopping simulator:', err);
            frappe.show_alert({
                message: __('Failed to stop simulator: ') + err.message,
                indicator: 'red'
            });
        });
}

// Status management functions
function update_port_status(frm) {
    const status_map = {
        'Connected': ['green', `Running on port ${frm.doc.server_port}`],
        'Disconnected': ['gray', 'Stopped'],
        'Connecting': ['yellow', 'Starting...'],
        'Error': ['red', 'Error']
    };

    const [color, message] = status_map[frm.doc.connection_status] || ['gray', frm.doc.connection_status];
    frm.page.set_indicator(message, color);
}

function setup_realtime_updates(frm) {
    cleanup_realtime_handlers();

    frappe.realtime.on('simulator_status_update', async (data) => {
        if (data.name === frm.doc.name) {
            frm.doc.connection_status = data.status;
            frm.doc.last_status_update = frappe.datetime.now_datetime();
            frm.doc._running = data.running;

            update_port_status(frm);
            setup_simulator_controls(frm);
            
            if (data.message) {
                frappe.show_alert({
                    message: data.message,
                    indicator: data.status === 'Connected' ? 'green' : 
                              data.status === 'Error' ? 'red' : 'yellow'
                });
            }

            await frm.reload_doc();
        }
    });

    frappe.realtime.on('simulator_value_update', (data) => {
        if (cur_dialog?.monitor_interval && data.name === frm.doc.name) {
            refresh_io_points(cur_dialog, frm);
        }
    });
}

function cleanup_realtime_handlers() {
    frappe.realtime.off('simulator_status_update');
    frappe.realtime.off('simulator_value_update');
}

// IO Monitor Dialog functions
function show_io_monitor(frm) {
    if (!frm.doc.io_points?.length) {
        frappe.show_alert({
            message: __('No I/O points configured'),
            indicator: 'yellow'
        });
        return;
    }

    const d = new frappe.ui.Dialog({
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

    refresh_io_points(d, frm);
    d.monitor_interval = setInterval(() => refresh_io_points(d, frm), 1000);
    d.onhide = () => clearInterval(d.monitor_interval);
    d.show();
}

function refresh_io_points(dialog, frm) {
    frm.call('get_io_points')
        .then(r => {
            if (r.message) {
                update_io_display(dialog, organize_io_points(r.message));
            }
        })
        .catch(err => {
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
    dialog.fields_dict.digital_outputs_html.$wrapper.html(generate_digital_outputs_html(points.digital_outputs));
    dialog.fields_dict.digital_inputs_html.$wrapper.html(generate_digital_inputs_html(points.digital_inputs));
    dialog.fields_dict.analog_html.$wrapper.html(generate_analog_html(points.analog_points));
}

// HTML Generation functions
function generate_digital_outputs_html(outputs) {
    if (!outputs?.length) {
        return '<div class="text-muted">No digital outputs configured</div>';
    }
    
    return `
        <div class="row">
            ${outputs.map(output => `
                <div class="col-sm-3 mb-3">
                    <div class="custom-control custom-switch">
                        <input type="checkbox" class="custom-control-input"
                            id="do_${output.modbus_address}"
                            ${output.value === '1' || output.toggle ? 'checked' : ''}
                            onchange="window.handle_output_change('${output.modbus_address}', this.checked)">
                        <label class="custom-control-label" for="do_${output.modbus_address}">
                            ${frappe.utils.escape_html(output.location_name)} (${output.modbus_address})
                        </label>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function generate_digital_inputs_html(inputs) {
    if (!inputs?.length) {
        return '<div class="text-muted">No digital inputs configured</div>';
    }
    
    return `
        <div class="row">
            ${inputs.map(input => `
                <div class="col-sm-3 mb-3">
                    <div class="indicator ${input.value === '1' ? 'green' : 'gray'}">
                        ${frappe.utils.escape_html(input.location_name)} (${input.modbus_address})
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function generate_analog_html(points) {
    if (!points?.length) {
        return '<div class="text-muted">No analog points configured</div>';
    }
    
    return `
        <div class="row">
            ${points.map(point => `
                <div class="col-sm-4 mb-3">
                    <div class="analog-point">
                        <label>${frappe.utils.escape_html(point.location_name)} (${point.modbus_address})</label>
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
                    onchange="window.handle_analog_change('${point.modbus_address}', this.value)">
            </div>
        `;
    }
    return '';
}

// Global event handlers
window.handle_output_change = async function(address, value) {
    try {
        const r = await frappe.call({
            method: 'set_output',
            args: {
                address: parseInt(address),
                value: value ? 1 : 0
            }
        });
        
        if (r.message) {
            frappe.show_alert({
                message: __(`Output ${address} set to ${value ? 'ON' : 'OFF'}`),
                indicator: 'green'
            });
        }
    } catch (err) {
        frappe.show_alert({
            message: __('Failed to set output value'),
            indicator: 'red'
        });
        console.error('Error setting output:', err);
    }
};

window.handle_analog_change = function(address, value) {
    frappe.call({
        method: 'set_holding_register',
        args: {
            address: parseInt(address),
            value: parseInt(value)
        }
    })
        .then(r => {
            if (r.message) {
                frappe.show_alert({
                    message: __(`Register ${address} set to ${value}`),
                    indicator: 'green'
                });
            }
        })
        .catch(err => {
            frappe.show_alert({
                message: __('Failed to set register value'),
                indicator: 'red'
            });
            console.error('Error setting register:', err);
        });
};