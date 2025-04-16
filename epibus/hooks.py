# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "epibus"
app_title = "EpiBus"
app_publisher = "Applied Relevance"
app_description = (
    "ERPNext integration with MODBUS/TCP networked programmable logic controllers (PLC)"
)
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "geveritt@appliedrelevance.com"
app_license = "MIT"

# Include additional assets for the Modbus Dashboard page
app_include_css = [
    "/assets/epibus/vendor/font-awesome/css/font-awesome.min.css"
]

fixtures = [
    {"dt": "Role", "filters": [
        ["name", "in", ["Modbus Administrator", "Modbus User"]]]},
    {"dt": "Workspace", "filters": [["name", "in", ["EpiBus"]]]},
    {"dt": "Server Script", "filters": [["module", "in", ["EpiBus"]]]},
    {"dt": "Custom Field", "filters": [["module", "in", ["EpiBus"]]]},
]

# epi_bus/hooks.py

fixtures = [

]

export_python_type_annotations = True

# Register virtual fields
docfield_list = {
    "Modbus Signal": [
        {"fieldname": "plc_address", "fieldtype": "Data"},
    ]
}

# Other hooks and configurations can be added below
# For example, including custom page JS/CSS or web templates if needed:
web_include_js = []
web_include_css = [
    "/assets/epibus/vendor/font-awesome/css/font-awesome.min.css",
]

# Scheduler configuration for signal monitoring

# Setup signal monitor on app install/update
# after_install = "epibus.epibus.install.after_install"

# Whitelisted methods
api_methods = {
    "epibus.www.warehouse_dashboard.get_modbus_data": ["GET"],
    "epibus.www.warehouse_dashboard.set_signal_value": ["POST"],
    "epibus.api.plc.get_signals": ["GET"],
    "epibus.api.plc.update_signal": ["POST"],
    "epibus.api.plc.get_plc_status": ["GET"],
    "epibus.api.plc.reload_signals": ["POST"]
}
