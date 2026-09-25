import frappe

from buzz.events.category_icons import CATEGORY_ICONS
from buzz.events.doctype.buzz_team.buzz_team import create_default_team_for
from buzz.utils import delete_custom_fields, get_custom_fields_creator

_create_custom_fields = get_custom_fields_creator("Buzz")

CRM_INTEGRATION_CUSTOM_FIELDS = {
	"CRM Lead": [
		{
			"fieldname": "buzz_tab",
			"label": "Buzz",
			"fieldtype": "Tab Break",
			"insert_after": "facebook_form_id",
		},
		{
			"fieldname": "buzz_campaign",
			"label": "Buzz Campaign",
			"fieldtype": "Link",
			"options": "Buzz Campaign",
			"insert_after": "buzz_tab",
		},
		{
			"fieldname": "buzz_column_break",
			"fieldtype": "Column Break",
			"insert_after": "buzz_campaign",
		},
		{
			"fieldname": "event_ticket",
			"label": "Event Ticket",
			"fieldtype": "Link",
			"options": "Event Ticket",
			"insert_after": "buzz_column_break",
		},
	],
}

USER_INVITATION_CUSTOM_FIELDS = {
	"User Invitation": [
		{
			"fieldname": "buzz_team",
			"label": "Buzz Team",
			"fieldtype": "Link",
			"options": "Buzz Team",
			"insert_after": "roles",
			"set_only_once": 1,
		},
		{
			"fieldname": "buzz_team_role",
			"label": "Buzz Team Role",
			"fieldtype": "Select",
			"options": "\nOwner\nAdmin\nManager\nFrontdesk\nViewer",
			"insert_after": "buzz_team",
			"set_only_once": 1,
		},
	],
}

ZOOM_INTEGRATION_CUSTOM_FIELDS = {
	"Buzz Event": [
		{
			"fieldname": "zoom_integration_tab",
			"label": "Zoom Integration",
			"fieldtype": "Tab Break",
			"insert_after": "ticket_print_format",
		},
		{
			"fieldname": "zoom_webinar",
			"label": "Zoom Webinar",
			"fieldtype": "Link",
			"options": "Zoom Webinar",
			"insert_after": "zoom_integration_tab",
		},
		{
			"fieldname": "zoom_meeting",
			"label": "Zoom Meeting",
			"fieldtype": "Link",
			"options": "Zoom Meeting",
			"insert_after": "zoom_webinar",
		},
	],
	"Buzz Settings": [
		{
			"fieldname": "zoom_integration_section",
			"label": "Zoom Integration Settings",
			"fieldtype": "Section Break",
			"insert_after": "custom_fields_go_after_this",
		},
		{
			"fieldname": "default_webinar_template",
			"label": "Default Webinar Template",
			"fieldtype": "Link",
			"options": "Zoom Webinar Template",
			"insert_after": "zoom_integration_section",
		},
	],
	"Buzz Team Settings": [
		{
			"fieldname": "zoom_integration_section",
			"label": "Zoom Integration Settings",
			"fieldtype": "Section Break",
			"insert_after": "custom_fields_go_after_this",
		},
		{
			"fieldname": "default_webinar_template",
			"label": "Default Webinar Template",
			"fieldtype": "Link",
			"options": "Zoom Webinar Template",
			"insert_after": "zoom_integration_section",
		},
	],
	"Event Ticket": [
		{
			"fieldname": "zoom_session_registration",
			"label": "Zoom Session Registration",
			"fieldtype": "Link",
			"options": "Zoom Session Registration",
			"insert_after": "ticket_type",
			"read_only": 1,
		},
	],
}


def before_tests():
	setup_test_records()


def setup_test_records():
	create_talk_proposal_statuses()

	# Administrator's only membership, so the team resolves for fixtures that omit one.
	admin_team = create_default_team_for("Administrator").name

	test_category = frappe.get_doc({"doctype": "Event Category", "name": "Test Category"}).insert(
		ignore_if_duplicate=True
	)
	test_venue = frappe.get_doc(
		{"doctype": "Event Venue", "name": "Test Venue", "address": "test", "team": admin_team}
	).insert(ignore_if_duplicate=True)
	test_host = frappe.get_doc(
		{"doctype": "Event Host", "host_name": "Test Host", "team": admin_team}
	).insert(ignore_if_duplicate=True)

	test_event_exists = frappe.db.exists("Buzz Event", {"route": "test-route"})
	if test_event_exists:
		frappe.delete_doc("Buzz Event", test_event_exists, force=True)
	frappe.get_doc(
		{
			"doctype": "Buzz Event",
			"team": admin_team,
			"category": test_category.name,
			"venue": test_venue.name,
			"host": test_host.name,
			"title": "Test Event",
			"route": "test-route",
			"start_date": frappe.utils.today(),
			"start_time": "10:00:00",
			"end_date": frappe.utils.add_days(frappe.utils.today(), 7),
			"end_time": "18:00:00",
		}
	).insert(ignore_if_duplicate=True)


def after_install():
	create_event_categories()
	create_talk_proposal_statuses()
	create_custom_fields()


def on_migrate():
	# insert is ignore_if_duplicate, so this only fills in categories added since install
	create_event_categories()
	create_talk_proposal_statuses()
	create_custom_fields()


def after_app_install(app_name: str):
	if app_name == "zoom_integration":
		create_zoom_integration_custom_fields()
	if app_name == "crm":
		create_crm_integration_custom_fields()


def after_app_uninstall(app_name: str):
	if app_name == "zoom_integration":
		delete_zoom_integration_custom_fields()
	if app_name == "crm":
		delete_crm_integration_custom_fields()


def create_custom_fields():
	installed_apps = frappe.get_installed_apps()

	_create_custom_fields(USER_INVITATION_CUSTOM_FIELDS, ignore_validate=True)

	if "zoom_integration" in installed_apps:
		create_zoom_integration_custom_fields()

	if "crm" in installed_apps:
		create_crm_integration_custom_fields()


def create_zoom_integration_custom_fields():
	_create_custom_fields(ZOOM_INTEGRATION_CUSTOM_FIELDS, ignore_validate=True)


def create_crm_integration_custom_fields():
	_create_custom_fields(CRM_INTEGRATION_CUSTOM_FIELDS, ignore_validate=True)


def delete_zoom_integration_custom_fields():
	delete_custom_fields(ZOOM_INTEGRATION_CUSTOM_FIELDS)


def delete_crm_integration_custom_fields():
	delete_custom_fields(CRM_INTEGRATION_CUSTOM_FIELDS)


def create_talk_proposal_statuses():
	statuses = [
		{"name": "Review Pending", "color": "Orange"},
		{"name": "Shortlisted", "color": "Blue"},
		{"name": "Accepted", "color": "Green"},
		{"name": "Rejected", "color": "Red"},
		{"name": "Replied", "color": "Blue"},
		{"name": "Duplicate", "color": "Gray"},
		{"name": "Withdrawn", "color": "Gray"},
	]

	for status in statuses:
		frappe.get_doc({"doctype": "Talk Proposal Status", **status}).insert(ignore_if_duplicate=True)


def create_event_categories():
	for name, icon_svg in CATEGORY_ICONS.items():
		frappe.get_doc(
			{"doctype": "Event Category", "name": name, "icon_svg": icon_svg, "enabled": 1}
		).insert(ignore_if_duplicate=True)
