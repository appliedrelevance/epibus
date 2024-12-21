frappe.pages['modbus-monitor'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Modbus Monitor',
        single_column: true
    });

    // Create monitor instance and pass the page
    page.monitor = new ModbusMonitor(page);

    // Add simulator selector field
    let field_wrapper = $('<div class="simulator-selector form-group"></div>')
        .prependTo(page.main.find('.layout-main-section'));
    
    let simulator_field = frappe.ui.form.make_control({
        parent: field_wrapper,
        df: {
            fieldname: 'simulator',
            label: __('PLC Simulator'),
            fieldtype: 'Link',
            options: 'PLC Simulator',
            reqd: 1,
            change() {
                if (page.monitor) {
                    page.monitor.refresh();
                }
            }
        },
        render_input: true
    });

    simulator_field.refresh();
    page.simulator_field = simulator_field;

    // Add styles
    frappe.dom.set_style(`
        .simulator-selector {
            padding: 15px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 15px;
        }
    `);
};

class ModbusMonitor {
    constructor(page) {
        this.page = page;
        this.make();
    }

    make() {
        // Create the main layout after any field wrappers
        let monitorHtml = `
            <div class="modbus-monitor">
                <div class="row">
                    <div class="col-md-4">
                        <div class="monitor-section">
                            <h6 class="text-muted">Digital Outputs</h6>
                            <div class="digital-outputs"></div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="monitor-section">
                            <h6 class="text-muted">Digital Inputs</h6>
                            <div class="digital-inputs"></div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="monitor-section">
                            <h6 class="text-muted">Analog I/O</h6>
                            <div class="analog-io"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        $(monitorHtml).appendTo(this.page.main.find('.layout-main-section'));
    }

    refresh() {
        const simulator = this.page.fields_dict.simulator.get_value();
        if (!simulator) {
            $(this.page.main).find('.modbus-monitor').html(`
                <div class="text-muted text-center">
                    <p>Please select a PLC Simulator to monitor</p>
                </div>
            `);
            return;
        }

        // Get simulator data including io_points
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'PLC Simulator',
                name: simulator
            },
            callback: (r) => {
                if (r.message) {
                    this.render_io_points(r.message.io_points || []);
                }
            }
        });
    }

    render_io_points(points) {
        const digital_outputs = points.filter(p => p.signal_type.includes('Digital Output'));
        const digital_inputs = points.filter(p => p.signal_type.includes('Digital Input'));
        const analog_points = points.filter(p => p.signal_type.includes('Analog'));

        // Render Digital Outputs
        let $outputs = $(this.page.main).find('.digital-outputs');
        $outputs.html(this.render_digital_outputs(digital_outputs));

        // Render Digital Inputs
        let $inputs = $(this.page.main).find('.digital-inputs');
        $inputs.html(this.render_digital_inputs(digital_inputs));

        // Render Analog I/O
        let $analog = $(this.page.main).find('.analog-io');
        $analog.html(this.render_analog_points(analog_points));

        this.setup_controls();
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
                    <div class="custom-control custom-switch">
                        <input type="checkbox" class="custom-control-input output-control"
                            id="out_${point.modbus_address}"
                            ${point.value === '1' ? 'checked' : ''}>
                        <label class="custom-control-label" 
                            for="out_${point.modbus_address}">
                            ${point.value === '1' ? 'ON' : 'OFF'}
                        </label>
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
            const address = $control.closest('.io-point').data('address');
            const value = $control.prop('checked') ? 1 : 0;
            
            this.set_output_value(address, value);
        });

        // Analog Output Controls
        $(this.page.main).find('.analog-control').on('change', (e) => {
            const $control = $(e.currentTarget);
            const address = $control.closest('.io-point').data('address');
            const value = parseInt($control.val());
            
            this.set_analog_value(address, value);
        });
    }

    set_output_value(address, value) {
        const simulator = this.page.fields_dict.simulator.get_value();
        if (!simulator) return;

        frappe.call({
            method: 'epibus.simulator.set_output',
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
        const simulator = this.page.fields_dict.simulator.get_value();
        if (!simulator) return;

        frappe.call({
            method: 'epibus.simulator.set_analog',
            args: {
                simulator: simulator,
                address: address,
                value: value
            },
            callback: (r) => {
                if (r.message) {
                    frappe.show_alert({
                        message: __(`Analog ${address} set to ${value}`),
                        indicator: 'green'
                    });
                }
            }
        });
    }
}