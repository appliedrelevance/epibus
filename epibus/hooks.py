from . import __version__ as app_version

app_name = "epibus"
app_title = "EpiBus"
app_publisher = "Applied Relevance"
app_description = (
    "ERPNext integration with MODBUS/TCP networked programmable logic controllers (PLC)"
)
app_email = "geveritt@appliedrelevance.com"
app_license = "MIT"

# After app startup
after_install = "epibus.epibus.utils.signal_monitor.setup_scheduler_job"

# Scheduler jobs
scheduler_jobs = [
    {
        "doctype": "Scheduled Job Type",
        "method": "epibus.epibus.utils.signal_monitor.check_signals",
        "frequency": "All",
    }
]
fixtures = [
    {
        "dt": "Role",
        "filters": [["name", "in", ["Modbus Administrator", "Modbus User"]]],
    },
    {"dt": "Workspace", "filters": [["name", "in", ["EpiBus"]]]},
]

page_js = {"modbus-monitor": "public/js/modbus_monitor.js"}

export_python_type_annotations = True


app_include_js = ["/assets/js/epibus.min.js"]  # Your bundled frontend

website_context = {"no_cache": 1, "include_session_info": True}  # This is important!
