// modbus_simulator.js

// Main form handler

frappe.ui.form.on('Modbus Simulator', {
    refresh: function (frm) {
        console.log('🔄 Form refresh:', {
            is_new: frm.is_new(),
            enabled: frm.doc.enabled,
            status: frm.doc.server_status
        });

        // Always allow editing unless server is running
        const isRunning = frm.doc.server_status === 'Running';

        // Setup action buttons based on state
        if (isRunning) {
            frm.add_custom_button(__('Stop Server'), () => handleStopServer(frm), __('Actions'));
            frm.add_custom_button(__('Test Connection'), () => handleTestConnection(frm), __('Actions'));
            frm.add_custom_button(__('Test Modbus Signals'), () => handleTestSignals(frm), __('Actions'));
            frm.add_custom_button(__('Verify Simulator Status'), () => handleVerifySimulatorStatus(frm), __('Actions'));
        } else if (frm.doc.enabled) {
            frm.add_custom_button(__('Start Server'), () => handleStartServer(frm), __('Actions'));
        }

        // Display server uptime
        if (frm.doc.server_status === 'Running') {
            updateServerUptime(frm);
            setInterval(() => updateServerUptime(frm), 1000); // Update every second
        }
    },

    enabled: function (frm) {
        // Handle enabled checkbox changes
        frm.dirty();  // Mark form as needing save
        frm.save();   // Trigger save to update state
    },

    validate: function (frm) {
        if (frm.doc.server_port < 1 || frm.doc.server_port > 65535) {
            frappe.throw(__('Port must be between 1 and 65535'));
            return false;
        }
        return true;
    },

    // Handle child table row events
    io_points_add: function (frm, cdt, cdn) {
        console.log('➕ Added new IO point row:', cdn);
    },

    io_points_remove: function (frm, cdt, cdn) {
        console.log('➖ Removed IO point row:', cdn);
    }
});

// Helper functions for UI feedback
const showAlert = (message, type) => {
    frappe.show_alert({
        message: __(message),
        indicator: type
    });
};

// Function to update server uptime
const updateServerUptime = (frm) => {
    const startTime = new Date(frm.doc.last_status_update);
    const now = new Date();
    const uptime = Math.floor((now - startTime) / 1000); // Uptime in seconds

    const hours = Math.floor(uptime / 3600);
    const minutes = Math.floor((uptime % 3600) / 60);
    const seconds = Math.floor(uptime % 60);

    frm.set_df_property('server_uptime', 'description', `${hours}h ${minutes}m ${seconds}s`);
};

// Dialog builder for signal test results
const buildSignalTestDialog = (results) => {
    const buildValueDisplay = (result) => {
        if (result.error) {
            return `<span class="text-danger">
                <i class="fa fa-exclamation-triangle"></i> ${result.error}
            </span>`;
        }

        if (result.type === "Digital Output Coil" || result.type === "Digital Input Contact") {
            const iconColor = result.value ? '#28a745' : '#dc3545';
            return `<div class="d-flex align-items-center">
                <svg height="12" width="12" style="margin-right: 8px;">
                    <circle cx="6" cy="6" r="5" fill="${iconColor}" />
                </svg>
                ${result.value ? 'ON' : 'OFF'}
            </div>`;
        }
        return `<span class="text-primary">${result.value}</span>`;
    };

    const buildSignalIcon = (signalName) => {
        const iconMap = {
            'green': 'text-success',
            'red': 'text-danger',
            'amber': 'text-warning'
        };
        const color = Object.entries(iconMap).find(([key]) => signalName.includes(key));
        return color ?
            `<i class="fa fa-circle ${color[1]} mr-2"></i>` :
            '<i class="fa fa-circle-o text-muted mr-2"></i>';
    };

    const content = `
        <style>
            .signal-test-results table { width: 100%; margin-bottom: 1rem; }
            .signal-test-results td { vertical-align: middle; padding: 0.75rem; }
            .signal-test-results .fa { margin-right: 8px; }
            .d-flex { display: flex; }
            .align-items-center { align-items: center; }
            .mr-2 { margin-right: 0.5rem; }
        </style>
        <div class="signal-test-results">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>Signal</th>
                        <th>Type</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    ${results.map(result => `
                        <tr>
                            <td>${buildSignalIcon(result.signal)}${result.signal}</td>
                            <td>${result.type || ''}</td>
                            <td>${buildValueDisplay(result)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    return new frappe.ui.Dialog({
        title: __('Modbus Signal Test Results'),
        fields: [{
            fieldtype: 'HTML',
            fieldname: 'results',
            options: content
        }],
        primary_action_label: __('Close'),
        primary_action: function () { this.hide(); }
    });
};

// Server control handlers
const handleStartServer = (frm) => {
    console.log('▶️ Initiating server start');
    showAlert('Starting Modbus server...', 'orange');

    return frm.call('start_simulator')
        .then((r) => {
            console.log('📨 Received start response:', r);
            if (r.message?.success) {
                console.log('✅ Start successful, reloading doc');
                return frm.reload_doc();
            }
            throw new Error(r.message?.error || 'Unknown error');
        })
        .then(() => {
            console.log('🔄 Document reloaded');
            showAlert('Modbus server started successfully', 'green');
            frm.refresh();
        })
        .catch((err) => {
            console.error('❌ Error starting server:', err);
            frappe.throw(__('Error starting server: ') + err.message);
        });
};

const handleStopServer = (frm) => {
    console.log('🛑 Initiating server stop');
    showAlert('Stopping Modbus server...', 'orange');

    return frm.call('stop_simulator')
        .then((r) => {
            console.log('📨 Received stop response:', r);
            if (r.message?.success) {
                console.log('✅ Stop successful, reloading doc');
                return frm.reload_doc();
            }
            throw new Error(r.message?.error || 'Unknown error');
        })
        .then(() => {
            console.log('🔄 Document reloaded');
            showAlert('Modbus server stopped successfully', 'blue');
            frm.refresh();
        })
        .catch((err) => {
            console.error('❌ Error stopping server:', err);
            frappe.throw(__('Error stopping server: ') + err.message);
        });
};

// Test handlers
const handleTestConnection = (frm) => {
    console.log('🔍 Testing connection');
    return frappe.call({
        method: 'epibus.epibus.doctype.modbus_simulator.modbus_simulator.test_connection',
        args: { simulator_name: frm.doc.name }
    })
        .then((r) => {
            console.log('📨 Received test response:', r);
            if (r.message?.success) {
                showAlert('Connection test successful', 'green');
            } else {
                throw new Error(r.message?.error || 'Unknown error');
            }
        })
        .catch((err) => {
            console.error('❌ Error testing connection:', err);
            frappe.throw(__('Error testing connection: ') + err.message);
        });
};

const handleTestSignals = (frm) => {
    console.log('🔍 Testing Modbus signals');
    return frappe.call({
        doc: frm.doc,
        method: 'test_modbus_signals',
        args: {}
    })
        .then((r) => {
            console.log('📨 Received test response:', r);
            if (r.message?.success) {
                const dialog = buildSignalTestDialog(r.message.results);
                dialog.show();
                showAlert('Modbus signal test successful', 'green');
            } else {
                throw new Error(r.message?.error || 'Unknown error');
            }
        })
        .catch((err) => {
            console.error('❌ Error testing Modbus signals:', err);
            frappe.throw(__('Error testing Modbus signals: ') + err.message);
        });
};

const handleVerifySimulatorStatus = (frm) => {
    console.log('🔍 Verifying simulator status');
    return frappe.call({
        method: 'epibus.epibus.doctype.modbus_simulator.modbus_simulator.verify_simulator_status',
        args: { simulator_name: frm.doc.name }
    })
        .then((r) => {
            console.log('📨 Received verification response:', r);
            if (r.message?.success) {
                showAlert('Simulator status verified successfully', 'green');
            } else {
                throw new Error(r.message?.error || 'Unknown error');
            }
        })
        .catch((err) => {
            console.error('❌ Error verifying simulator status:', err);
            frappe.throw(__('Error verifying simulator status: ') + err.message);
        });
};

// Handle field changes in child table rows
frappe.ui.form.on('Modbus Signal', {
    signal_type: function (frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        console.log('📝 Signal type changed:', row.signal_type, 'in row:', cdn);

        // Toggle value fields based on type
        if (row.signal_type.includes('Digital')) {
            frappe.model.set_value(cdt, cdn, 'float_value', null);
        } else {
            frappe.model.set_value(cdt, cdn, 'digital_value', 0);
        }

        // Recalculate PLC address
        calculate_plc_address(frm, row);
    },

    modbus_address: function (frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        console.log('🔢 Modbus address changed:', row.modbus_address, 'in row:', cdn);

        // Recalculate PLC address
        calculate_plc_address(frm, row);
    }
});

// Helper function to calculate PLC address
function calculate_plc_address(frm, row) {
    if (!row.signal_type) return;

    frappe.call({
        doc: row,
        method: 'calculate_plc_address',
        args: {
            signal_type: row.signal_type,
            modbus_address: row.modbus_address
        },
        callback: function (r) {
            if (r.docs[0]) {
                plc_address = r.docs[0].plc_address;
                frappe.model.set_value(row.doctype, row.name, 'plc_address', plc_address);
                console.log('🏭 PLC address calculated:', plc_address, 'for row:', row.name);
            }
        }
    });
}