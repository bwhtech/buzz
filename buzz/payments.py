import frappe
from bwh_payments import api as payments
from frappe import _


def get_payment_gateways_for_event(event: str) -> list[str]:
	"""Get the event's own payment gateways, or the site default when it has none.

	Only enabled gateways are returned, so a gateway switched off in bwh_payments is never offered.
	"""
	gateways = frappe.get_all(
		"Event Payment Gateway",
		filters={"parent": event, "parenttype": "Buzz Event"},
		pluck="payment_gateway",
	)
	default = frappe.db.get_single_value("Buzz Settings", "default_payment_gateway")
	enabled = set(payments.get_payment_gateways())
	return [gateway for gateway in gateways or [default] if gateway in enabled]


def resolve_payment_gateway(event: str, payment_gateway: str | None) -> str:
	"""The gateway the client picked, as long as the event takes payments through it."""
	gateways = get_payment_gateways_for_event(event)
	if not gateways:
		frappe.throw(_("No payment gateway configured for this event"))
	if payment_gateway and payment_gateway not in gateways:
		frappe.throw(_("{0} is not a payment gateway for this event").format(payment_gateway))
	return payment_gateway or gateways[0]


def get_payment_link_for_booking(
	booking_id: str, redirect_to: str = "/events", payment_gateway: str | None = None
) -> str:
	booking_doc = frappe.get_cached_doc("Event Booking", booking_id)
	payment_gateway = resolve_payment_gateway(booking_doc.event, payment_gateway)
	return get_payment_link(
		"Event Booking",
		booking_id,
		booking_doc.total_amount,
		booking_doc.currency,
		payment_gateway,
		redirect_to=redirect_to,
	)


def get_payment_link_for_sponsorship(
	sponsorship_enquiry: str,
	sponsorship_tier: str,
	redirect_to: str = "/events",
	payment_gateway: str | None = None,
	currency: str | None = None,
) -> str:
	tier_doc = frappe.get_cached_doc("Sponsorship Tier", sponsorship_tier)
	if not tier_doc.enabled:
		frappe.throw(_("This sponsorship tier is no longer available."))
	payment_gateway = resolve_payment_gateway(tier_doc.event, payment_gateway)
	price = tier_doc.price_for(currency)
	frappe.db.set_value(
		"Sponsorship Enquiry", sponsorship_enquiry, "tier", sponsorship_tier
	)  # TODO: rethink later

	return get_payment_link(
		"Sponsorship Enquiry",
		sponsorship_enquiry,
		price.price,
		price.currency,
		payment_gateway,
		redirect_to,
	)


def get_payment_link(
	reference_doctype: str,
	reference_docname: str,
	amount: float,
	currency: str,
	payment_gateway: str,
	redirect_to: str = "/events",
) -> str:
	"""Open a checkout and return its URL. bwh_payments brings the shopper back to `redirect_to`."""
	payments.validate_currency(payment_gateway, currency)
	payment = record_payment(reference_doctype, reference_docname, amount, currency, payment_gateway)
	payment_request = payments.create_payment(
		reference_doctype,
		reference_docname,
		amount,
		currency,
		payment_gateway,
		redirect_to=redirect_to,
		**get_customer_details(),
	)
	payment.db_set({"payment_request": payment_request.name, "order_id": payment_request.order_ref})
	return payment_request.order_url


def get_customer_details() -> dict:
	if frappe.session.user == "Guest":
		return {}
	first_name, last_name = frappe.get_cached_value("User", frappe.session.user, ["first_name", "last_name"])
	return {
		"customer_email": frappe.session.user,
		"customer_forenames": first_name,
		"customer_surname": last_name,
	}


def record_payment(
	reference_doctype: str,
	reference_docname: str,
	amount: float,
	currency: str,
	payment_gateway: str | None = None,
):
	payment_doc = frappe.new_doc("Event Payment")
	payment_doc.update(
		{
			"user": frappe.session.user,
			"amount": amount,
			"currency": currency,
			"reference_doctype": reference_doctype,
			"reference_docname": reference_docname,
			"payment_gateway": payment_gateway,
		}
	)
	payment_doc.save(ignore_permissions=True)
	return payment_doc


def mark_payment_as_received(reference_doctype: str, reference_docname: str):
	"""Mark the Event Payment whose checkout bwh_payments has confirmed as received."""
	payment_request = frappe.db.get_value(
		"Gateway Payment Request",
		{"ref_doctype": reference_doctype, "ref_docname": reference_docname, "status": "Paid"},
		["name", "gateway_transaction_ref"],
		as_dict=True,
		order_by="creation desc",
	)
	if not payment_request:
		return

	frappe.db.set_value(
		"Event Payment",
		{"payment_request": payment_request.name},
		{"payment_received": 1, "payment_id": payment_request.gateway_transaction_ref},
	)


# TODO: use it later!
def save_address(address):
	filters = {"email_id": frappe.session.user}
	exists = frappe.db.exists("Address", filters)
	if exists:
		address_doc = frappe.get_last_doc("Address", filters=filters)
	else:
		address_doc = frappe.new_doc("Address")

	address_doc.update(address)
	address_doc.update(
		{
			"address_title": frappe.db.get_value("User", frappe.session.user, "full_name"),
			"address_type": "Billing",
			"is_primary_address": 1,
			"email_id": frappe.session.user,
		}
	)
	address_doc.save(ignore_permissions=True)
	return address_doc.name
