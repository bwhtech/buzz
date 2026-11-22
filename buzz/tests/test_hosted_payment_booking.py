import json
from unittest.mock import patch

import frappe
from bwh_payments import testing as payment_testing
from bwh_payments.bwh_payments.checkout import get_return_url, return_from_gateway
from bwh_payments.bwh_payments.doctype.razorpay_gateway_settings.razorpay_gateway_settings import (
	RazorpayGatewaySettings,
)
from frappe.utils import get_url

from buzz.api.booking import process_booking
from buzz.api.booking.schemas import BookingRequest
from buzz.api.hosted_payments import confirm_checkout, return_to_site
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

	def test_booking_sends_the_buyer_to_the_hub_pay_page(self):
		payment_link = self.book()
		self.assertEqual(payment_link, get_url(f"/pay/{self.pro_payment_request().order_ref}"))

	def test_booking_paid_in_the_hub_dialog_is_confirmed_on_return(self):
		self.book()
		pro_request = self.pro_payment_request()
		order_id = pro_request.order_ref
		dialog_result = payment_testing.complete_embedded_checkout(self.hub_payment_request(order_id))
		with patch("frappe.sendmail"):
			with self.set_user("Guest"):
				status = confirm_checkout(order_id, dialog_result)
			site_return = self.follow_as_guest(return_to_site, order_id)
			success_page = self.follow_as_guest(return_from_gateway, pro_request.name)

		self.assertEqual(status, "Paid")
		self.assertEqual(site_return, f"{get_return_url(pro_request.name)}&order_id={order_id}")
		booking = frappe.get_doc("Event Booking", pro_request.ref_docname)
		self.assertTrue(success_page.startswith(f"/b/booking-success/{booking.name}?token="))
		self.assertEqual((booking.docstatus, booking.status), (1, "Confirmed"))

	def test_redirect_gateway_returns_the_buyer_to_the_pay_page(self):
		with patch.object(RazorpayGatewaySettings, "supports_embedded_checkout", False):
			self.book()
		order_id = self.pro_payment_request().order_ref
		hub_request = self.hub_payment_request(order_id)
		payment_testing.pay(hub_request)
		self.assertEqual(self.follow_as_guest(return_from_gateway, hub_request), f"/pay/{order_id}")

	def test_return_before_paying_leaves_the_booking_unconfirmed(self):
		self.book()
		pro_request = self.pro_payment_request()
		self.follow_as_guest(return_from_gateway, pro_request.name)
		booking = frappe.get_doc("Event Booking", pro_request.ref_docname)
		self.assertEqual(booking.docstatus, 0)

	def ping(self, body: dict) -> None:
		payment_testing.post_webhook(BUZZ_GATEWAY, json.dumps(body).encode(), {})

	def test_ping_for_a_paid_order_confirms_the_booking_without_the_return(self):
		self.book()
		pro_request = self.pro_payment_request()
		with patch("frappe.sendmail"):
			payment_testing.pay(self.hub_payment_request(pro_request.order_ref))
			self.ping({"order_id": pro_request.order_ref})
		booking = frappe.get_doc("Event Booking", pro_request.ref_docname)
		self.assertEqual((booking.docstatus, booking.status), (1, "Confirmed"))

	def test_ping_status_is_read_from_the_hub_not_the_body(self):
		self.book()
		pro_request = self.pro_payment_request()
		self.ping({"order_id": pro_request.order_ref, "status": "Paid"})
		self.assertEqual(
			frappe.db.get_value("Gateway Payment Request", pro_request.name, "status"), "Pending"
		)
		self.assertEqual(frappe.db.get_value("Event Booking", pro_request.ref_docname, "docstatus"), 0)

	def test_ping_without_an_order_is_ignored(self):
		self.ping({"status": "Paid"})
		self.assertFalse(frappe.db.exists("Error Log", {"method": "Buzz webhook verification failed"}))

	def confirmed_booking(self):
		self.book()
		pro_request = self.pro_payment_request()
		with patch("frappe.sendmail"):
			payment_testing.pay(self.hub_payment_request(pro_request.order_ref))
			self.follow_as_guest(return_from_gateway, pro_request.name)
		return frappe.get_doc("Event Booking", pro_request.ref_docname), pro_request.order_ref

	def booking_refund(self, booking: str):
		return frappe.get_last_doc("Event Booking Refund", {"booking": booking})

	def test_booking_refund_from_the_desk_is_made_on_the_hub(self):
		booking, order_id = self.confirmed_booking()
		with patch("frappe.sendmail"):
			booking.refund(amount=200)
		self.assertEqual(frappe.db.get_value("Hosted Payment", order_id, "refunded_amount"), 200)
		self.assertEqual(self.booking_refund(booking.name).status, "Processed")

	def test_pending_hub_refund_settles_on_sync(self):
		booking, order_id = self.confirmed_booking()
		payment_testing.set_next_refund_status("Pending")
		booking.refund(amount=200)
		self.assertEqual(self.booking_refund(booking.name).status, "Initiated")
		hub_refund = frappe.get_last_doc("Gateway Refund", {"reference": order_id})
		payment_testing.send_refund_webhook(hub_refund.name, "Processed")
		with patch("frappe.sendmail"):
			booking.sync_refunds()
		self.assertEqual(frappe.db.get_value("Hosted Payment", order_id, "refunded_amount"), 200)
		self.assertEqual(self.booking_refund(booking.name).status, "Processed")

	def test_pending_hub_refund_settles_on_the_hub_ping(self):
		booking, order_id = self.confirmed_booking()
		payment_testing.set_next_refund_status("Pending")
		booking.refund(amount=200)
		hub_refund = frappe.get_last_doc("Gateway Refund", {"reference": order_id})
		payment_testing.send_refund_webhook(hub_refund.name, "Processed")
		with patch("frappe.sendmail"):
			self.ping({"order_id": order_id})
		self.assertEqual(self.booking_refund(booking.name).status, "Processed")
