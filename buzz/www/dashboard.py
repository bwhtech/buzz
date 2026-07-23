# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.utils import get_system_timezone

no_cache = 1


def get_context():
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()  # nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit
	context = frappe._dict()
	context.boot = get_boot()
	context.boot.csrf_token = csrf_token
	return context


# nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
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
		}
	)
