frappe.pages['modbus-monitor'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Modbus Monitor',
        single_column: true
    });

    // Add page level filters
    page.add_field({
        fieldname: 'simulator',
        label: __('PLC Simulator'),
        fieldtype: 'Link',
        options: 'PLC Simulator',
        change() {
            page.monitor.refresh();
        }
    });

    // Create and attach the Monitor class instance
    page.monitor = new ModbusMonitor(page);
}

frappe.pages['modbus-monitor'].on_page_show = function(wrapper) {
    // Refresh when page is shown
    if (wrapper.page.monitor) {
        wrapper.page.monitor.refresh();
    }
}

class ModbusMonitor {
    constructor(page) {
        this.page = page;
        this.make();
        this.setup_socket();
    }

    make() {
        // Create the main layout
        $(this.page.main).html(`
            <div class="modbus-monitor">
                <div class="row">
                    <div class="col-md-4">
                        <div class="monitor-section">
                            <h6 class="text-muted uppercase">Digital Outputs</h6>
                            <div class="digital-outputs"></div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="monitor-section">
                            <h6 class="text-muted uppercase">Digital Inputs</h6>
                            <div class="digital-inputs"></div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="monitor-section">
                            <h6 class="text-muted uppercase">Analog I/O</h6>
                            <div class="analog-io"></div>
                        </div>
                    </div>
                </div>
            </div>
        `);

        // Add styles
        frappe.dom.set_style(`
            .modbus-monitor .monitor-section {
                padding: 15px;
                border: 1px solid var(--border-color);
                border-radius: var(--border-radius-md);
                margin-bottom: 15px;
            }
            .modbus-monitor .uppercase {
                text-transform: uppercase;
                font-size: 11px;
                font-weight: 600;
            }
            .modbus-monitor .io-point {
                margin: 10px 0;
                padding: 10px;
                background: var(--bg-light-gray);
                border-radius: var(--border-radius-sm);
            }
            .modbus-monitor .io-value {
                font-weight: 600;
            }
            .modbus-monitor .io-controls {
                margin-top: 5px;
            }
        `);
    }

    setup_socket() {
        // Listen for value updates
        frappe.realtime.on('simulator_value_update', (data) => {
            if (data.name === this.get_current_simulator()) {
                this.refresh_values(data);
            }
        });

        // Listen for status updates
        frappe.realtime.on('simulator_status_update', (data) => {
            if (data.name === this.get_current_simulator()) {
                this.handle_status_update(data);
            }
        });
    }

    get_current_simulator() {
        return this.page.fields_dict.simulator.get_value();
    }

    refresh() {
        const simulator = this.get_current_simulator();
        if (!simulator) {
            this.show_no_simulator_message();
            return;
        }

        frappe.call({
            method: 'epibus.epibus.doctype.plc_simulator.plc_simulator.get_io_points',
            args: { name: simulator },
            callback: (r) => {
                if (r.message) {
                    this.render_io_points(r.message);
                }
            }
        });
    }

    render_io_points(points) {
        const organized = this.organize_points(points);
        
        // Render Digital Outputs
        const $outputs = $(this.page.main).find('.digital-outputs');
        $outputs.html(this.render_digital_outputs(organized.digital_outputs));

        // Render Digital Inputs
        const $inputs = $(this.page.main).find('.digital-inputs');
        $inputs.html(this.render_digital_inputs(organized.digital_inputs));

        // Render Analog I/O
        const $analog = $(this.page.main).find('.analog-io');
        $analog.html(this.render_analog_points(organized.analog_points));

        // Setup event handlers
        this.setup_controls();
    }

    organize_points(points) {
        return {
            digital_outputs: points.filter(p => p.signal_type.includes('Digital Output')),
            digital_inputs: points.filter(p => p.signal_type.includes('Digital Input')),
            analog_points: points.filter(p => p.signal_type.includes('Analog'))
        };
    }

    render_digital_outputs(outputs) {
        if (!outputs.length) return '<div class="text-muted">No digital outputs configured</div>';

        return outputs.map(point => `
            <div class="io-point" data-address="${point.modbus_address}">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <div>${frappe.utils.escape_html(point.location_name)}</div>
                        <div class="text-muted">Address: ${point.modbus_address}</div>
                    </div>
                    <div class="io-controls">
                        <div class="custom-control custom-switch">
                            <input type="checkbox" class="custom-control-input output-control"
                                id="out_${point.modbus_address}"
                                data-address="${point.modbus_address}"
                                ${point.value === '1' ? 'checked' : ''}>
                            <label class="custom-control-label" 
                                for="out_${point.modbus_address}">
                                ${point.value === '1' ? 'ON' : 'OFF'}
                            </label>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    render_digital_inputs(inputs) {
        if (!inputs.length) return '<div class="text-muted">No digital inputs configured</div>';

        return inputs.map(point => `
            <div class="io-point" data-address="${point.modbus_address}">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <div>${frappe.utils.escape_html(point.location_name)}</div>
                        <div class="text-muted">Address: ${point.modbus_address}</div>
                    </div>
                    <div class="indicator ${point.value === '1' ? 'green' : 'gray'}">
                        ${point.value === '1' ? 'ON' : 'OFF'}
                    </div>
                </div>
            </div>
        `).join('');
    }

    render_analog_points(points) {
        if (!points.length) return '<div class="text-muted">No analog points configured</div>';

        return points.map(point => `
            <div class="io-point" data-address="${point.modbus_address}">
                <div>
                    <div>${frappe.utils.escape_html(point.location_name)}</div>
                    <div class="text-muted">Address: ${point.modbus_address}</div>
                    <div class="io-value">${point.value || '0'}</div>
                    ${this.render_analog_controls(point)}
                </div>
            </div>
        `).join('');
    }

    render_analog_controls(point) {
        if (point.signal_type.includes('Output')) {
            return `
                <div class="io-controls">
                    <input type="range" class="form-control-range analog-control"
                        data-address="${point.modbus_address}"
                        min="0" max="65535" value="${point.value || 0}">
                </div>
            `;
        }
        return '';
    }

    setup_controls() {
        // Digital Output Controls
        $(this.page.main).find('.output-control').on('change', (e) => {
            const $control = $(e.currentTarget);
            const address = $control.data('address');
            const value = $control.prop('checked') ? 1 : 0;
            
            this.set_output_value(address, value);
        });

        // Analog Output Controls
        $(this.page.main).find('.analog-control').on('change', (e) => {
            const $control = $(e.currentTarget);
            const address = $control.data('address');
            const value = parseInt($control.val());
            
            this.set_analog_value(address, value);
        });
    }

    set_output_value(address, value) {
        const simulator = this.get_current_simulator();
        if (!simulator) return;

        frappe.call({
            method: 'epibus.epibus.doctype.plc_simulator.plc_simulator.set_output',
            args: {
                simulator: simulator,
                address: address,
                value: value
            },
            callback: (r) => {
                if (r.message) {
                    frappe.show_alert({
                        message: __(`Output ${address} set to ${value ? 'ON' : 'OFF'}`),
                        indicator: 'green'
                    });
                }
            }
        });
    }

    set_analog_value(address, value) {
        const simulator = this.get_current_simulator();
        if (!simulator) return;

        frappe.call({
            method: 'epibus.epibus.doctype.plc_simulator.plc_simulator.set_holding_register',
            args: {
                simulator: simulator,
                address: address,
                value: value
            },
            callback: (r) => {
                if (r.message) {
                    frappe.show_alert({
                        message: __(`Register ${address} set to ${value}`),
                        indicator: 'green'
                    });
                }
            }
        });
    }

    refresh_values(data) {
        // Update Digital Outputs
        data.digital_outputs?.forEach(point => {
            const $point = $(this.page.main).find(`.io-point[data-address="${point.address}"]`);
            if ($point.length) {
                $point.find('.output-control').prop('checked', point.value === '1');
                $point.find('.custom-control-label').text(point.value === '1' ? 'ON' : 'OFF');
            }
        });

        // Update Digital Inputs
        data.digital_inputs?.forEach(point => {
            const $point = $(this.page.main).find(`.io-point[data-address="${point.address}"]`);
            if ($point.length) {
                const $indicator = $point.find('.indicator');
                $indicator
                    .removeClass('gray green')
                    .addClass(point.value === '1' ? 'green' : 'gray')
                    .text(point.value === '1' ? 'ON' : 'OFF');
            }
        });

        // Update Analog Values
        data.analog_points?.forEach(point => {
            const $point = $(this.page.main).find(`.io-point[data-address="${point.address}"]`);
            if ($point.length) {
                $point.find('.io-value').text(point.value);
                $point.find('.analog-control').val(point.value);
            }
        });
    }

    handle_status_update(data) {
        if (data.status === 'Error') {
            frappe.show_alert({
                message: __(`Simulator Error: ${data.message}`),
                indicator: 'red'
            });
        }
    }

    show_no_simulator_message() {
        $(this.page.main).find('.modbus-monitor').html(`
            <div class="text-muted text-center">
                <p>Please select a PLC Simulator to monitor</p>
            </div>
        `);
    }
}