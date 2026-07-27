import frappe
from frappe.model.utils.rename_field import rename_field

from buzz.install import create_zoom_integration_custom_fields

DOCTYPE = "Event Ticket"
OLD_FIELD = "zoom_webinar_registration"
NEW_FIELD = "zoom_session_registration"


def execute():
	"""Follow zoom_integration renaming Zoom Webinar Registration -> Zoom Session Registration.

	No-op on sites without zoom_integration, where the custom field was never created.
	"""
	if not frappe.db.has_column(DOCTYPE, OLD_FIELD):
		return

	# rename_field copies values into an existing field, it does not create one. The
	# after_migrate hook that creates our custom fields runs after patches, so do it here.
	create_zoom_integration_custom_fields()

	rename_field(DOCTYPE, OLD_FIELD, NEW_FIELD)

	# the old column is left behind for `bench trim-tables` to reclaim
	frappe.delete_doc("Custom Field", f"{DOCTYPE}-{OLD_FIELD}", ignore_missing=True, force=True)
