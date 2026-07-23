import frappe
from frappe import _
from payments.utils import get_payment_gateway_controller


def get_payment_gateway_for_event(event: str):
	return frappe.get_cached_value("Buzz Event", event, "payment_gateway")


def get_payment_gateways_for_event(event: str) -> list[str]:
	"""Get all payment gateways configured for an event."""
	gateways = frappe.get_all(
		"Event Payment Gateway",
		filters={"parent": event, "parenttype": "Buzz Event"},
		pluck="payment_gateway",
	)
	if not gateways:
		# Fallback to legacy field
		legacy = frappe.get_cached_value("Buzz Event", event, "payment_gateway")
		return [legacy] if legacy else []
	return gateways


def get_controller(payment_gateway):
	return get_payment_gateway_controller(payment_gateway)


@frappe.whitelist()
def get_payment_link_for_booking(
	booking_id: str, redirect_to: str = "/events", payment_gateway: str | None = None
) -> str:
	booking_doc = frappe.get_cached_doc("Event Booking", booking_id)
	event_title = frappe.get_cached_value("Buzz Event", booking_doc.event, "title")
	if not payment_gateway:
		gateways = get_payment_gateways_for_event(booking_doc.event)
		if not gateways:
			frappe.throw(_("No payment gateway configured for this event"))
		payment_gateway = gateways[0]
	return get_payment_link(
		"Event Booking",
		booking_id,
		booking_doc.total_amount,
		booking_doc.currency,
		payment_gateway,
		redirect_to=redirect_to,
		title=f"Payment for {event_title}",
	)


@frappe.whitelist()
def get_payment_link_for_sponsorship(
	sponsorship_enquiry: str,
	sponsorship_tier: str,
	redirect_to: str = "/events",
	payment_gateway: str | None = None,
) -> str:
	tier_doc = frappe.get_cached_doc("Sponsorship Tier", sponsorship_tier)
	if not payment_gateway:
		gateways = get_payment_gateways_for_event(tier_doc.event)
		if not gateways:
			frappe.throw(_("No payment gateway configured for this event"))
		payment_gateway = gateways[0]
	event_title = frappe.get_cached_value("Buzz Event", tier_doc.event, "title")
	frappe.db.set_value(
		"Sponsorship Enquiry", sponsorship_enquiry, "tier", sponsorship_tier
	)  # TODO: rethink later

	return get_payment_link(
		"Sponsorship Enquiry",
		sponsorship_enquiry,
		tier_doc.price,
		tier_doc.currency,
		payment_gateway,
		redirect_to,
		f"Payment for {tier_doc.title} Sponsorship at {event_title}",
	)


def get_payment_link(
	reference_doctype: str,
	reference_docname: str,
	amount: float,
	currency: str,
	payment_gateway: str,
	redirect_to: str = "/events",
	title: str | None = None,
) -> str:
	payment = record_payment(reference_doctype, reference_docname, amount, currency, payment_gateway)
	controller = get_controller(payment_gateway)
	user_full_name = frappe.get_cached_value("User", frappe.session.user, "full_name")

	payment_details = {
		"amount": amount,
		"title": title or f"Payment for {reference_doctype}: {reference_docname}",
		"description": f"{user_full_name}'s payment for {reference_doctype} (#{reference_docname})",
		"reference_doctype": reference_doctype,
		"reference_docname": reference_docname,
		"payer_email": frappe.session.user,
		"payer_name": user_full_name,
		"currency": currency,
		"payment_gateway": payment_gateway,
		"redirect_to": redirect_to,
		"payment": payment.name,
	}
	if payment_gateway == "Razorpay" or payment_gateway == "Paymob":
		order = controller.create_order(**payment_details)
		payment_details.update({"order_id": order.get("id")})

	url = controller.get_payment_url(**payment_details)

	return url


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
	if frappe.in_test:
		return

	import json

	request = frappe.get_all(
		"Integration Request",
		{
			"reference_doctype": reference_doctype,
			"reference_docname": reference_docname,
		},
		order_by="creation desc",
		limit=1,
	)

	if len(request):
		data = frappe.db.get_value("Integration Request", request[0].name, "data")
		data = frappe._dict(json.loads(data))

		payment_gateway = data.get("payment_gateway")
		if payment_gateway == "Razorpay":
			payment_id = "razorpay_payment_id"

		elif payment_gateway == "Paymob":
			payment_id = "paymob_payment_id"

		elif payment_gateway == "PayPal":
			payment_id = "transaction_id"

		elif "Stripe" in payment_gateway:
			payment_id = "stripe_token_id"
		else:
			payment_id = "order_id"

		frappe.db.set_value(
			"Event Payment",
			data.payment,
			{
				"payment_received": 1,
				"payment_id": data.get(payment_id),
				"order_id": data.get("order_id"),
			},
		)

		frappe.db.commit()  # nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit


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
