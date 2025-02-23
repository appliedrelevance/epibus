frappe.provide('epibus.modbus');

epibus.modbus.Dashboard = class ModbusDashboard {
    constructor() {
        this.signals = new Set();  // Track monitored signals
        this.init();
    }

    init() {
        // Subscribe to realtime updates
        frappe.realtime.on('modbus_signal_update', (data) => {
            this.handleSignalUpdate(data);
        });

        // Start monitoring signals that aren't already being monitored
        this.startMonitoringNewSignals();
    }

    handleSignalUpdate(data) {
        if (!data || !data.signal) return;

        const signalName = data.signal;
        const value = data.value;

        // Update internal state
        this.signals[signalName] = value;

        // Update UI
        this.updateSignalDisplay(signalName, value);
    }

    updateSignalDisplay(signalName, value) {
        // Find the signal row
        const row = $(`.modbus-signal-row[data-signal="${signalName}"]`);
        if (!row.length) return;

        // Update value display
        const valueDisplay = row.find('.signal-value');
        if (typeof value === 'boolean') {
            valueDisplay.html(`
                <div class="signal-indicator ${value ? 'green' : 'red'}">
                    ${value ? 'TRUE' : 'FALSE'}
                </div>
                <button class="signal-toggle btn btn-default btn-sm" data-signal="${signalName}" data-value="${value}">
                    Toggle
                </button>
            `);

            // Bind click handler for toggle button
            valueDisplay.find('.signal-toggle').on('click', (e) => {
                const btn = $(e.currentTarget);
                const signalName = btn.data('signal');

                frappe.call({
                    method: 'epibus.epibus.doctype.modbus_signal.modbus_signal.toggle_signal',
                    args: {
                        signal_name: signalName
                    },
                    callback: (r) => {
                        if (r.message !== undefined) {
                            this.handleSignalUpdate({
                                signal: signalName,
                                value: r.message
                            });
                        }
                    }
                });
            });
        } else {
            valueDisplay.text(value);
        }
    }

    startMonitoringNewSignals() {
        // Get initial data
        frappe.call({
            method: 'epibus.www.modbus_dashboard.get_modbus_data',
            callback: (r) => {
                if (!r.message) return;

                // Process each connection's signals
                r.message.forEach(connection => {
                    connection.signals.forEach(signal => {
                        // Update UI with initial value
                        this.updateSignalDisplay(signal.name, signal.value);

                        // Start monitoring if not already monitoring
                        if (!this.signals.has(signal.name)) {
                            this.signals.add(signal.name);
                            frappe.call({
                                method: 'epibus.epibus.utils.signal_monitor.start_monitoring',
                                args: { signal_id: signal.name }
                            });
                        }
                    });
                });
            }
        });
    }
}

// Initialize dashboard when document ready
$(document).ready(() => {
    if ($('.modbus-dashboard').length) {
        window.modbus_dashboard = new epibus.modbus.Dashboard();
    }
});

// Add custom styles
frappe.dom.set_style(`
    .signal-indicator {
        display: inline-flex;
        align-items: center;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .signal-indicator.green {
        background-color: var(--green-100);
        color: var(--green-600);
    }
    .signal-indicator.red {
        background-color: var(--red-100);
        color: var(--red-600);
    }
`);