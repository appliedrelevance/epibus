from . import __version__ as app_version

app_name = "epibus"
app_title = "Epibus"
app_publisher = "Applied Relevance"
app_description = (
    "ERPNext integration with MODBUS/TCP networked programmable logic controllers (PLC)"
)
app_email = "geveritt@appliedrelevance.com"
app_license = "MIT"


# Document Events
# ---------------
# Hook on document methods and events
# hooks.py

doc_events = {
    "Stock Entry": {
        "on_submit": "epibus.epibus.doctype.modbus_action.modbus_action.handle_submit"
    },
}


fixtures = [
    {"dt": "Role", "filters": [["name", "in", ["Modbus Administrator", "Modbus User"]]]}
]

# In your app's hooks.py

scheduler_events = {
    "all": [
        # List of functions to be executed in all sites every X time
    ],
    "hourly": [
        # Other hourly tasks
    ],
    "daily": [
        # Other daily tasks
    ],
    "weekly": [
        # Other weekly tasks
    ],
    "monthly": [
        # Other monthly tasks
    ],
    "cron": {
        # Here, we define a custom schedule for updating the Modbus server status
        "*/5 * * * *": [  # Every 5 minutes; adjust the timing as needed
            "epibus.epibus.doctype.modbus_server.modbus_server.update_status"
        ]
    },
}


# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/epibus/css/epibus.css"
# app_include_js = "/assets/epibus/js/epibus.js"

# include js, css files in header of web template
# web_include_css = "/assets/epibus/css/epibus.css"
# web_include_js = "/assets/epibus/js/epibus.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "epibus/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "epibus.utils.jinja_methods",
# 	"filters": "epibus.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "epibus.install.before_install"
# after_install = "epibus.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "epibus.uninstall.before_uninstall"
# after_uninstall = "epibus.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "epibus.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"epibus.tasks.all"
# 	],
# 	"daily": [
# 		"epibus.tasks.daily"
# 	],
# 	"hourly": [
# 		"epibus.tasks.hourly"
# 	],
# 	"weekly": [
# 		"epibus.tasks.weekly"
# 	],
# 	"monthly": [
# 		"epibus.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "epibus.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "epibus.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "epibus.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"epibus.auth.validate"
# ]
