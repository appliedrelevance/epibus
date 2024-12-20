frappe.pages['modbus-monitor'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'PLC Simulator',
		single_column: true
	});
}