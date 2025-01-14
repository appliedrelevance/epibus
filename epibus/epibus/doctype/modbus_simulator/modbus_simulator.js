// Copyright (c) 2024, Applied Relevance and contributors
// For license information, please see license.txt

frappe.ui.form.on('Modbus Simulator', {
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

    // Setup new handler for status updates only
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
}