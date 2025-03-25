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
web_include_js = []
web_include_css = [
    "/assets/epibus/vendor/font-awesome/css/font-awesome.min.css",
]

# Scheduler configuration for signal monitoring
scheduler_events = {
    "all": [
        "epibus.epibus.utils.signal_monitor.check_signals"
    ]
}

# Setup signal monitor on app install/update
after_install = "epibus.utils.signal_monitor.setup_scheduler_job"
after_app_install = "epibus.utils.plc_worker_job.start_plc_worker"
after_app_restore = "epibus.utils.plc_worker_job.start_plc_worker"

# Also start on system startup
on_session_creation = [
    "epibus.utils.plc_worker_job.start_plc_worker"
]

# Whitelisted methods
api_methods = {
    "epibus.epibus.utils.signal_monitor.start_monitoring": ["POST"],
    "epibus.www.warehouse_dashboard.get_modbus_data": ["GET"],
    "epibus.www.warehouse_dashboard.set_signal_value": ["POST"],
    "epibus.api.plc.get_signals": ["GET"],
    "epibus.api.plc.update_signal": ["POST"],
    "epibus.api.plc.get_plc_status": ["GET"],
    "epibus.api.plc.reload_signals": ["POST"]
}
