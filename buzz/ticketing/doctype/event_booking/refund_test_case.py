from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.payments import handle_refund_notification
from buzz.tests.factories import (
	BuzzEventFactory,
	EventBookingFactory,
	EventPaymentFactory,
	EventTicketTypeFactory,
	IntegrationRequestFactory,
	PaymentGatewayFactory,
)
from buzz.ticketing.doctype.event_booking.event_booking import RAZORPAY

TICKET_PRICE = 500
# 500 per ticket with 10% tax on top.
CHARGED_PER_TICKET = 550.0
GATEWAY_CONTROLLER = "buzz.ticketing.doctype.event_booking.event_booking.get_controller"


class BookingRefundTestCase(IntegrationTestCase):
	"""A paid booking of one ticket per price in `ticket_prices`, on an event with 10% tax."""

	ticket_prices = (TICKET_PRICE, TICKET_PRICE)
	attendee_names = ("John", "Jenny")

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = cls.create_event()
		cls.ticket_types = [
			EventTicketTypeFactory.create(event=cls.event, prices=[{"currency": "INR", "price": price}]).name
			for price in cls.ticket_prices
		]
		cls.gateway = razorpay_gateway()

	@classmethod
	def create_event(cls) -> str:
		return BuzzEventFactory.create("with_tax", tax_percentage=10).name

	def setUp(self):
		self.enterContext(self.set_user("Administrator"))
		self.booking = self.create_paid_booking(self.attendee_names, self.ticket_types)

	def create_paid_booking(self, names, ticket_types):
		attendees = [
			{"ticket_type": ticket_type, "first_name": name, "email": f"{name.lower()}@example.com"}
			for name, ticket_type in zip(names, ticket_types, strict=True)
		]
		booking = EventBookingFactory.create(event=self.event, attendees=attendees, payment_status="Paid")
		booking.submit()
		return booking

	def make_payment(self, gateway: str | None = None):
		self.payment = EventPaymentFactory.create(
			"received",
			user=self.booking.user,
			amount=self.booking.total_amount,
			currency=self.booking.currency,
			reference_doctype="Event Booking",
			reference_docname=self.booking.name,
			payment_gateway=gateway or self.gateway,
		)

	def initiate_refund(self, amount: float, tickets: list[str] | None = None, refund_id: str | None = None):
		client = MagicMock()
		client.refund_payment.return_value = {
			"id": refund_id or self.refund_id(),
			"status": "pending",
			"amount": int(amount * 100),
		}
		with patch(GATEWAY_CONTROLLER, return_value=client):
			self.booking.refund(amount=amount, tickets=tickets)
		self.booking.reload()
		return client

	def send_refund_webhook(self, refund_id: str, status: str, amount: float) -> str:
		log = self.create_refund_log(self.refund_payload(refund_id, status, amount))
		self.handle_refund_log(log)
		return log

	def refund_payload(self, refund_id: str, status: str, amount: float) -> dict:
		entity = {
			"id": refund_id,
			"status": status,
			"amount": int(amount * 100),
			"payment_id": self.payment.payment_id,
		}
		return {"event": f"refund.{status}", "payload": {"refund": {"entity": entity}}}

	def create_refund_log(self, payload: dict) -> str:
		return IntegrationRequestFactory.create(data=frappe.as_json(payload)).name

	def handle_refund_log(self, log: str) -> None:
		# Cancelling a ticket emails the attendee, and delivery is not under test.
		with patch("frappe.sendmail"):
			handle_refund_notification("Integration Request", log)
		self.booking.reload()

	def refund_id(self, suffix: str = "1") -> str:
		"""Refund ids are unique in the database, and rollback is per class."""
		return f"rfnd_{self._testMethodName}_{suffix}"

	def refunds(self) -> list:
		names = frappe.get_all(
			"Event Booking Refund",
			filters={"booking": self.booking.name},
			order_by="creation asc",
			pluck="name",
		)
		return [frappe.get_doc("Event Booking Refund", name) for name in names]

	def refundable_tickets(self) -> list[str]:
		return [ticket["ticket"] for ticket in self.booking.get_refund_summary()["tickets"]]

	def cancellation_requests(self) -> list:
		return frappe.get_all(
			"Ticket Cancellation Request",
			filters={"booking": self.booking.name},
			fields=["name", "docstatus"],
		)


def razorpay_gateway() -> str:
	"""Refunds only go through a gateway named Razorpay, so this name is fixed."""
	if not frappe.db.exists("Payment Gateway", RAZORPAY):
		PaymentGatewayFactory.create(gateway=RAZORPAY)
	return RAZORPAY
