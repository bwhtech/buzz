# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.utils import get_system_timezone

from buzz import telemetry
from buzz.analytics import posthog_config
from buzz.api.maps.services import place_search_enabled
from buzz.events.doctype.buzz_team.buzz_team import personal_teams_enabled
from buzz.playground import playground_boot
from buzz.utils import is_app_installed
from buzz.www.event.venue_map import google_maps_embed_api_key

no_cache = 1


def get_context():
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()  # nosemgrep: frappe-manual-commit
	context = frappe._dict()
	context.boot = get_boot()
	context.boot.csrf_token = csrf_token
	context.link_preview = form_link_preview(frappe.request.path if frappe.request else "")
	if frappe.session.user != "Guest":
		telemetry.capture("active_site", interval="1d", on_commit=False)
	return context


def form_link_preview(path: str) -> dict | None:
	"""Link previews read the HTML, so a public form's page carries its own title and description."""
	parts = path.strip("/").split("/")
	if len(parts) != 3 or parts[0] != "b":
		return None
	from buzz.api.forms import form_service
	from buzz.api.forms.services import RegistrationFormService

	try:
		if parts[1] == "register":
			return RegistrationFormService(parts[2]).link_preview()
		return form_service(parts[1], parts[2]).link_preview()
	except frappe.ValidationError:
		frappe.clear_messages()
		return None


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw(_("This method is only meant for developer mode"))
	return get_boot()


def get_boot():
	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"site_name": frappe.local.site,
			"read_only_mode": frappe.flags.read_only,
			"system_timezone": get_system_timezone(),
			"google_place_search_enabled": place_search_enabled(),
			"google_maps_embed_api_key": google_maps_embed_api_key(),
			"zoom_available": is_app_installed("zoom_integration"),
			"playground": playground_boot(),
			"posthog_config": posthog_config(),
			"personal_teams_enabled": personal_teams_enabled(),
		}
	)
