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
    "/assets/epibus/vendor/font-awesome/css/font-awesome.min.css",
    "/assets/epibus/css/modbus_dashboard.css"
]

fixtures = [
    {
        "dt": "Role",
        "filters": [["name", "in", ["Modbus Administrator", "Modbus User"]]],
    },
    {"dt": "Workspace", "filters": [["name", "in", ["EpiBus"]]]},
    {"dt": "Server Script", "filters": [["module", "in", ["EpiBus"]]]},
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
web_include_js = ["/assets/epibus/js/modbus_dashboard.js"]
web_include_css = [
    "/assets/epibus/vendor/font-awesome/css/font-awesome.min.css",
    "/assets/epibus/css/modbus_dashboard.css",
]

# Scheduler configuration for signal monitoring
scheduler_events = {
    "all": [
        "epibus.epibus.utils.signal_monitor.check_signals"
    ]
}

# Setup signal monitor on app install/update
after_install = "epibus.epibus.utils.signal_monitor.setup_scheduler_job"

# Whitelisted methods
api_methods = {
    "epibus.epibus.utils.signal_monitor.start_monitoring": ["POST"]
}
