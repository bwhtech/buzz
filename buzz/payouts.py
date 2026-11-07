from datetime import timedelta
from zoneinfo import ZoneInfo

import frappe
from bwh_payments import api as payments
from frappe.utils import flt, get_system_timezone

from buzz.utils import build_event_datetimes, datetime_in_time_zone

PAYOUT_HOLD_DAYS = 2
# Razorpay takes about 2% plus a 0.25% transfer fee, both with GST, from our balance.
MINIMUM_PLATFORM_FEE_PERCENT = 3
EVENT_END_FIELDS = ("start_date", "start_time", "end_date", "end_time", "time_zone")
PAID_DOCTYPES = ("Event Booking", "Sponsorship Enquiry")


class PayoutSplit:
	"""The team's share of one payment, which the gateway holds until shortly after the event."""

	def __init__(self, event: str | int, amount: float, currency: str, gateway: str):
		self.event = frappe.get_cached_doc("Buzz Event", event)
		self.amount = flt(amount)
		self.currency = currency
		self.gateway = gateway
		self.fee_percent = flt(frappe.db.get_single_value("Buzz Settings", "platform_fee_percent"))

	def as_list(self) -> list[dict]:
		"""The `splits` for `payments.create_payment`: none when the team cannot be paid this way."""
		linked_account = self.get_linked_account()
		if not linked_account:
			return []
		return [
			{
				"linked_account": linked_account,
				"amount": self.team_share(),
				"hold_until": get_payout_hold(self.event),
			}
		]

	def get_linked_account(self) -> str | None:
		if not (self.fee_percent and self.event.team):
			return None
		if not payments.supports_splits(self.gateway, self.currency):
			return None
		return payments.get_linked_account(self.gateway, "Buzz Team", self.event.team)

	def team_share(self) -> float:
		paid = payments.to_minor_units(self.amount, self.currency)
		fee = round(paid * self.fee_percent / 100)
		return payments.from_minor_units(paid - fee, self.currency)


def get_payout_hold(event):
	"""The event's end plus PAYOUT_HOLD_DAYS, in the system time zone like every Datetime field."""
	_start, end = build_event_datetimes(event)
	end = datetime_in_time_zone(event.time_zone, end) or end
	if end.tzinfo:
		end = end.astimezone(ZoneInfo(get_system_timezone())).replace(tzinfo=None)
	return end + timedelta(days=PAYOUT_HOLD_DAYS)


def move_event_holds(event_name: str):
	"""Hold the team's share of every payment for the event until after its new end."""
	hold_until = get_payout_hold(frappe.get_doc("Buzz Event", event_name))
	for payment_request in get_routed_payment_requests(event_name):
		try:
			payments.set_split_hold(payment_request, hold_until)
		except Exception:
			frappe.log_error(title=f"Could not move the payout hold on {payment_request}")


def get_routed_payment_requests(event: str) -> list[str]:
	"""The paid payment requests for `event` that send a share on to the team."""
	requests = []
	for doctype in PAID_DOCTYPES:
		names = frappe.get_all(doctype, filters={"event": event}, pluck="name")
		requests += frappe.get_all(
			"Event Payment",
			filters={
				"reference_doctype": doctype,
				"reference_docname": ("in", names or [""]),
				"payment_received": 1,
			},
			pluck="payment_request",
		)
	return frappe.get_all(
		"Gateway Payment Split", filters={"parent": ("in", requests or [""])}, pluck="parent", distinct=True
	)
