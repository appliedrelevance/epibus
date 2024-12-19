frappe.ui.form.on('Modbus Signal', {
    toggle: function (frm) {
        // When the 'toggle' field changes, call a Python method to update the pin and read the value back
        frm.call({
            method: 'toggle_location_pin',
            args: {},
            callback: function (r) {
                if (r.message) {
                    // Update the 'value' field with the read value
                    frm.set_value('value', r.message);
                }
            }
        });
    }
});
