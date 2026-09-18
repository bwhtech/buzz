import frappe
from frappe import _
from frappe.utils import flt
from payments.payment_gateways.doctype.razorpay_settings.razorpay_settings import razorpay_api_call
from payments.utils import get_payment_gateway_controller
from pydantic import AliasPath, BaseModel, ConfigDict, Field

from buzz.ticketing.doctype.event_booking_refund.event_booking_refund import record_gateway_refund

RAZORPAY = "Razorpay"

# What a paid Razorpay status means to a document's `on_payment_authorized`.
PAID_STATUSES = {"captured": "Completed", "authorized": "Authorized"}


class RefundNotification(BaseModel):
	"""The refund a Razorpay `refund.processed` or `refund.failed` webhook carries.

	The fields sit at `payload.refund.entity` in the webhook body, and every one
	of them is mandatory: the payments app hands us refund events only, and a
	refund event without them is broken rather than uninteresting.
	"""

	model_config = ConfigDict(extra="ignore")

	refund_id: str = Field(validation_alias=AliasPath("payload", "refund", "entity", "id"))
	payment_id: str = Field(validation_alias=AliasPath("payload", "refund", "entity", "payment_id"))
	status: str = Field(validation_alias=AliasPath("payload", "refund", "entity", "status"))
	amount_in_minor_unit: int = Field(validation_alias=AliasPath("payload", "refund", "entity", "amount"))

	@property
	def amount(self) -> float:
		"""What the gateway refunded, in the major unit the booking is priced in."""
		return flt(self.amount_in_minor_unit) / 100


def get_payment_gateways_for_event(event: str) -> list[str]:
	"""Get all payment gateways configured for an event."""
	return frappe.get_all(
		"Event Payment Gateway",
		filters={"parent": event, "parenttype": "Buzz Event"},
		pluck="payment_gateway",
	)


def get_controller(payment_gateway):
	return get_payment_gateway_controller(payment_gateway)


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


def get_payment_link_for_sponsorship(
	sponsorship_enquiry: str,
	sponsorship_tier: str,
	redirect_to: str = "/events",
	payment_gateway: str | None = None,
) -> str:
	tier_doc = frappe.get_cached_doc("Sponsorship Tier", sponsorship_tier)
	if not tier_doc.enabled:
		frappe.throw(_("This sponsorship tier is no longer available."))
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
		data = frappe.parse_json(data)

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

		if not frappe.in_test:
			frappe.db.commit()  # nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit


def get_checkout_request(reference_doctype: str, reference_docname: str) -> frappe._dict | None:
	"""The Integration Request holding the gateway order for this document."""
	# A checkout logs two of them, and only the one behind the checkout link has an order id.
	logs = frappe.get_all(
		"Integration Request",
		{"reference_doctype": reference_doctype, "reference_docname": reference_docname},
		["name", "data"],
		order_by="creation desc",
	)

	for log in logs:
		data = frappe.parse_json(log.data)
		if str(data.get("order_id") or "").startswith("order_"):
			return frappe._dict(name=log.name, data=data)


def fetch_order_payments(controller, order_id: str) -> list[dict]:
	"""Every payment the gateway holds against an order."""
	with razorpay_api_call("order payment list"):
		return controller.get_client().order.payments(order_id).get("items", [])


def sync_gateway_payment(reference_doctype: str, reference_docname: str) -> str:
	"""Apply what the gateway holds for this document's order.

	A payment the browser never reported back leaves the document waiting on money the
	gateway already took. Returns the status applied, or "" when there was nothing to apply.
	"""
	checkout = get_checkout_request(reference_doctype, reference_docname)
	if not checkout:
		return ""

	# Locked, because a late browser callback can be confirming the same payment right now.
	payment = frappe.db.get_value(
		"Event Payment",
		checkout.data.get("payment"),
		["payment_gateway", "payment_received"],
		as_dict=True,
		for_update=True,
	)
	if not payment or payment.payment_received:
		return ""

	# Only Razorpay can be asked about an order today, and the hourly sweep walks every
	# unpaid booking, so another gateway is nothing to sync rather than an error.
	if payment.payment_gateway != RAZORPAY:
		return ""

	controller = get_controller(payment.payment_gateway)
	for gateway_payment in fetch_order_payments(controller, checkout.data["order_id"]):
		if gateway_payment.get("status") in PAID_STATUSES:
			return apply_gateway_payment(checkout, gateway_payment, reference_doctype, reference_docname)

	return ""


def apply_gateway_payment(
	checkout: frappe._dict, gateway_payment: dict, reference_doctype: str, reference_docname: str
) -> str:
	"""Run the confirmation a live checkout would have run for this gateway payment."""
	status = PAID_STATUSES[gateway_payment["status"]]

	# The document reads the payment id back off the checkout log, exactly as it does after a
	# live checkout, so this writes it where `mark_payment_as_received` already looks.
	frappe.db.set_value(
		"Integration Request",
		checkout.name,
		{
			"data": frappe.as_json({**checkout.data, "razorpay_payment_id": gateway_payment["id"]}),
			"status": status,
		},
	)
	frappe.get_doc(reference_doctype, reference_docname).run_method("on_payment_authorized", status)

	return status


def handle_refund_notification(doctype: str, docname: str) -> None:
	"""Apply a gateway refund webhook to the booking whose payment it belongs to."""
	# Returns nothing on purpose: `call_hook_method` stops at the first handler
	# that returns a value.
	payload = frappe.parse_json(frappe.db.get_value(doctype, docname, "data"))
	notification = RefundNotification.model_validate(payload)

	payment = frappe.db.get_value(
		"Event Payment",
		{"payment_id": notification.payment_id},
		["name", "reference_doctype", "reference_docname"],
		as_dict=True,
	)

	if not payment or payment.reference_doctype != "Event Booking":
		return

	# The same event arrives more than once, so the refund is keyed on its id.
	record_gateway_refund(
		booking=payment.reference_docname,
		payment=payment.name,
		refund_id=notification.refund_id,
		status=notification.status,
		amount=notification.amount,
	)

	frappe.db.set_value(
		doctype,
		docname,
		{"reference_doctype": "Event Booking", "reference_docname": payment.reference_docname},
		update_modified=False,
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
