import frappe
from frappe import _

from buzz.api.hosted_payments.checkout import SETTLED_STATUSES, HostedCheckout

no_cache = 1


def get_context(context):
	order_id = frappe.form_dict.order_id
	if not (order_id and frappe.db.exists("Hosted Payment", order_id)):
		raise frappe.PageDoesNotExistError

	config = HostedCheckout(order_id).page_config()
	if config["status"] in SETTLED_STATUSES:
		frappe.flags.redirect_location = config["return_url"]
		# Not 301: browsers cache a permanent redirect.
		raise frappe.Redirect(http_status_code=302)

	context.config = config
	context.title = _("Payment")
