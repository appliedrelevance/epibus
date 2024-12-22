// epibus/epibus/page/modbus_monitor/modbus_monitor.js
frappe.pages['modbus-monitor'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Modbus Monitor',
        single_column: true
    });

    // Add the React mount point
    $(wrapper).find('.layout-main-section').html('<div id="plc-simulator-root"></div>');

    // Load your React app
    frappe.require('/assets/epibus/frontend/main.js').then(() => {
        if (window.mountPLCSimulator) {
            window.mountPLCSimulator('plc-simulator-root');
        }
    });
};