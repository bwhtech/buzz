from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.booking.schemas import BookingRequest
from buzz.api.booking.services import create_add_on_doc
from buzz.payments import handle_refund_notification
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	EventBookingFactory,
	EventPaymentFactory,
	EventSponsorFactory,
	EventTicketTypeFactory,
	IntegrationRequestFactory,
	PaymentGatewayFactory,
	SponsorshipEnquiryFactory,
	SponsorshipTierFactory,
	TicketAddOnFactory,
	UserFactory,
)
from buzz.ticketing.doctype.event_booking.event_booking import RAZORPAY

BOOKER = "booking-owner@example.com"
OUTSIDER = "booking-outsider@example.com"
TICKET_PRICE = 500
ADD_ON_PRICE = 200
# 500 per ticket with 10% tax on top.
CHARGED_PER_TICKET = 550.0
GATEWAY_CONTROLLER = "buzz.ticketing.doctype.event_booking.event_booking.get_controller"


class BookingTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.booker = UserFactory.create_once(BOOKER).name
		cls.outsider = UserFactory.create_once(OUTSIDER).name
		cls.event = BuzzEventFactory.create()
		cls.event.reload()

	def setUp(self):
		self.enterContext(self.set_user("Administrator"))
		frappe.clear_messages()
		self.addCleanup(frappe.clear_document_cache, "Buzz Event", self.event.name)
		self.set_event({"is_published": 1, "registrations_close_at": None, "allow_guest_booking": 0})
		self.free_ticket_type = EventTicketTypeFactory.create(event=self.event.name)

	def set_event(self, values):
		frappe.db.set_value("Buzz Event", self.event.name, values)
		frappe.clear_document_cache("Buzz Event", self.event.name)

	def enable_phone_otp(self):
		self.set_event({"allow_guest_booking": 1, "guest_verification_method": "Phone OTP"})

	def booking_request(self, **overrides):
		values = {
			"attendees": [
				{
					"first_name": "Booker",
					"email": "booker@example.com",
					"ticket_type": str(self.free_ticket_type.name),
				}
			],
			"event": str(self.event.name),
		}
		values.update(overrides)
		return BookingRequest(**values)


class SponsorshipTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = str(BuzzEventFactory.create().name)

	def setUp(self):
		self.enterContext(self.set_user("Administrator"))
		frappe.clear_messages()
		self.tier = SponsorshipTierFactory.create(
			event=self.event, title="Gold", prices=[{"currency": "INR", "price": 5000}]
		)
		self.enquiry = SponsorshipEnquiryFactory.create(
			event=self.event, tier=self.tier.name, company_name="Acme Corp", company_logo="/files/acme.png"
		)

	def make_stranger(self) -> str:
		return UserFactory.create_once("sponsorship-stranger@example.com").name

	def make_sponsor(self):
		return EventSponsorFactory.create(
			event=self.event,
			tier=self.tier.name,
			enquiry=self.enquiry.name,
			company_name="Acme Corp",
			company_logo="/files/acme.png",
		)


class CouponTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create()
		cls.ticket_type = create_paid_ticket_type(cls.event.name)
		cls.add_on = TicketAddOnFactory.create(event=cls.event.name, price=ADD_ON_PRICE)

	def create_booking(self, coupon: str, count: int = 1, **overrides):
		attendees = attendee_rows(self.ticket_type.name, count)
		return EventBookingFactory.create(
			event=self.event.name, coupon_code=coupon, attendees=attendees, **overrides
		)

	def create_booking_with_add_on(self, coupon: str, count: int = 1):
		attendees = attendee_rows(self.ticket_type.name, count)
		attendees[0]["add_ons"] = create_add_on_doc("", [{"add_on": self.add_on.name, "value": "XL"}]).name
		return EventBookingFactory.create(event=self.event.name, coupon_code=coupon, attendees=attendees)

	def assert_amounts(self, booking, net: int, discount: int, total: int):
		amounts = (booking.net_amount, booking.discount_amount, booking.total_amount)
		self.assertEqual(amounts, (net, discount, total))


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


class TeamPermissionTestCase(IntegrationTestCase):
	"""Alice owns team A, Bob owns team B, and each team has one unpublished event."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.alice = UserFactory.create_once("perm-alice@example.com").name
		cls.bob = UserFactory.create_once("perm-bob@example.com").name
		cls.outsider = UserFactory.create_once("perm-outsider@example.com").name
		cls.team_a = BuzzTeamFactory.create_owned_by(cls.alice, team_name="Perm Team A").name
		cls.team_b = BuzzTeamFactory.create_owned_by(cls.bob, team_name="Perm Team B").name
		cls.event_a = BuzzEventFactory.create("unpublished", team=cls.team_a).name
		cls.event_b = BuzzEventFactory.create("unpublished", team=cls.team_b).name

	def setUp(self):
		self.enterContext(self.set_user("Administrator"))

	def has_permission_as(self, user: str, ptype: str, doctype: str, doc: str) -> bool:
		with self.set_user(user):
			return frappe.has_permission(doctype, ptype, doc=doc)

	def list_as(self, user: str, doctype: str, pluck: str = "name") -> list:
		with self.set_user(user):
			return frappe.get_list(doctype, pluck=pluck)


def create_paid_ticket_type(event, price: int = TICKET_PRICE):
	return EventTicketTypeFactory.create(event=event, prices=[{"currency": "INR", "price": price}])


def attendee_rows(ticket_type, count: int) -> list[dict]:
	return [
		{
			"ticket_type": ticket_type,
			"first_name": f"Attendee {index}",
			"email": f"attendee{index}@example.com",
		}
		for index in range(count)
	]


def razorpay_gateway() -> str:
	"""Refunds only go through a gateway named Razorpay, so this name is fixed."""
	if not frappe.db.exists("Payment Gateway", RAZORPAY):
		PaymentGatewayFactory.create(gateway=RAZORPAY)
	return RAZORPAY
