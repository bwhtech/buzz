from unittest.mock import patch

import frappe
from bwh_payments import testing as payment_testing
from bwh_payments.bwh_payments.checkout import get_return_url, return_from_gateway

from buzz.api.booking import process_booking
from buzz.api.booking.schemas import BookingRequest
from buzz.api.hosted_payments import return_to_site
from buzz.tests.base_test_cases import BUZZ_GATEWAY, BuzzGatewayTestCase, create_paid_ticket_type
from buzz.tests.factories import BuzzEventFactory, BuzzFormFactory, UserFactory


class TestHostedPaymentBooking(BuzzGatewayTestCase):
	"""A Pro booking paid on the hub's checkout, then confirmed when the buyer comes back."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# process_booking commits; held so the class rollback still undoes the bookings.
		cls.held_commits = payment_testing.without_commits()
		cls.held_commits.__enter__()
		cls.booker = UserFactory.create_once("hosted-payment-booker@example.com").name
		cls.event = str(BuzzEventFactory.create(payment_gateways=[{"payment_gateway": BUZZ_GATEWAY}]).name)
		BuzzFormFactory.set_registration_cutoff(cls.event, None)
		cls.ticket_type = str(create_paid_ticket_type(cls.event).name)

	@classmethod
	def tearDownClass(cls):
		cls.held_commits.__exit__(None, None, None)
		super().tearDownClass()

	def book(self) -> str:
		attendee = {"first_name": "Booker", "email": "booker@example.com", "ticket_type": self.ticket_type}
		request = BookingRequest(event=self.event, payment_gateway=BUZZ_GATEWAY, attendees=[attendee])
		with self.set_user(self.booker):
			return process_booking(request).payment_link

	def pro_payment_request(self):
		booking = frappe.get_last_doc("Event Booking", {"event": self.event})
		payment = frappe.get_last_doc("Event Payment", {"reference_docname": booking.name})
		return frappe.get_doc("Gateway Payment Request", payment.payment_request)

	def follow_as_guest(self, endpoint, argument: str) -> str:
		with self.set_user("Guest"):
			endpoint(argument)
		return frappe.local.response["location"]

	def test_booking_sends_the_buyer_to_the_hub_checkout(self):
		payment_link = self.book()
		hub_request = self.hub_payment_request(self.pro_payment_request().order_ref)
		self.assertEqual(
			payment_link, frappe.db.get_value("Gateway Payment Request", hub_request, "order_url")
		)

	def test_booking_paid_on_the_hub_is_confirmed_on_return(self):
		self.book()
		pro_request = self.pro_payment_request()
		order_id = pro_request.order_ref
		hub_request = self.hub_payment_request(order_id)
		with patch("frappe.sendmail"):
			payment_testing.pay(hub_request)
			hub_return = self.follow_as_guest(return_from_gateway, hub_request)
			site_return = self.follow_as_guest(return_to_site, order_id)
			success_page = self.follow_as_guest(return_from_gateway, pro_request.name)

		self.assertEqual(
			hub_return, f"/api/method/buzz.api.hosted_payments.return_to_site?order_id={order_id}"
		)
		self.assertEqual(site_return, f"{get_return_url(pro_request.name)}&order_id={order_id}")
		booking = frappe.get_doc("Event Booking", pro_request.ref_docname)
		self.assertTrue(success_page.startswith(f"/b/booking-success/{booking.name}?token="))
		self.assertEqual((booking.docstatus, booking.status), (1, "Confirmed"))

	def test_return_before_paying_leaves_the_booking_unconfirmed(self):
		self.book()
		pro_request = self.pro_payment_request()
		self.follow_as_guest(return_from_gateway, pro_request.name)
		booking = frappe.get_doc("Event Booking", pro_request.ref_docname)
		self.assertEqual(booking.docstatus, 0)
