app_name = "buzz"
app_title = "Buzz"
app_publisher = "BWH Studios"
app_description = "Event Management App built on Frappe"
app_email = "hussain@buildwithhussain.com"
app_license = "agpl-3.0"

# Apps
# ------------------

required_apps = ["frappe/payments"]

export_python_type_annotations = True

after_install = "buzz.install.after_install"

before_uninstall = "buzz.uninstall.before_uninstall"


website_route_rules = [
	{"from_route": "/b", "to_route": "dashboard"},
	{"from_route": "/b/<path:app_path>", "to_route": "dashboard"},
]

# Keep old /dashboard/* links working: redirect to the shortened /b/* scheme.
# Ordered specific -> catch-all; the first matching source wins.
website_redirects = [
	{"source": r"/dashboard/events/([^/]+)/forms/([^/]+)", "target": r"/b/\1/\2"},
	{"source": r"/dashboard/book-tickets/(.+)", "target": r"/b/register/\1"},
	{"source": r"/dashboard/(.*)", "target": r"/b/\1"},
]

# Scheduled Tasks
# ---------------

scheduler_events = {"daily": ["buzz.tasks.unpublish_ticket_types_after_last_date"]}

# Testing
# -------

before_tests = "buzz.install.before_tests"


doc_events = {
	"User": {
		"after_insert": "buzz.utils.add_buzz_user_role",
		"on_update": "buzz.events.doctype.speaker_profile.speaker_profile.update_speaker_display_name",
	},
}

fixtures = [{"dt": "Role", "filters": {"name": ["in", ["Buzz User", "Frontdesk Manager"]]}}]

user_invitation = {"allowed_roles": {"Event Manager": ["Buzz User"], "Buzz User": ["Buzz User"]}}


ignore_links_on_delete = ["Ticket Cancellation Request", "Ticket Add-on Value"]

after_app_install = "buzz.install.after_app_install"

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
	{
		"name": "buzz",
		"logo": "/assets/buzz/images/buzz-logo-rounded.png",
		"title": "Buzz",
		"route": "/app/buzz",
		"has_permission": "buzz.api.has_app_permission",
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/events/css/events.css"
# app_include_js = "/assets/buzz/js/events.js"

# include js, css files in header of web template
# web_include_css = "/assets/events/css/events.css"
# web_include_js = "/assets/events/js/events.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "events/public/scss/website"

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

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "events/public/icons.svg"

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

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "events.utils.jinja_methods",
# 	"filters": "events.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "events.install.before_install"

# Uninstallation
# ------------

# before_uninstall = "events.uninstall.before_uninstall"
# after_uninstall = "events.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "events.utils.before_app_install"


# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "events.utils.before_app_uninstall"
after_app_uninstall = "buzz.install.after_app_uninstall"
after_migrate = "buzz.install.on_migrate"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "events.notifications.get_notification_config"

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

# Document Events
# ---------------
# Hook on document methods and events


# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "events.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "events.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["events.utils.before_request"]
# after_request = ["events.utils.after_request"]

# Job Events
# ----------
# before_job = ["events.utils.before_job"]
# after_job = ["events.utils.after_job"]

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
# 	"events.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
