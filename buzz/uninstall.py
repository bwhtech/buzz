from buzz.install import USER_INVITATION_CUSTOM_FIELDS, ZOOM_INTEGRATION_CUSTOM_FIELDS
from buzz.utils import delete_custom_fields


def before_uninstall():
	delete_custom_fields_for_zoom_integration()
	delete_custom_fields(USER_INVITATION_CUSTOM_FIELDS)


def before_app_uninstall(app_name):
	if app_name == "zoom_integration":
		delete_custom_fields_for_zoom_integration()


def delete_custom_fields_for_zoom_integration():
	delete_custom_fields(ZOOM_INTEGRATION_CUSTOM_FIELDS)
