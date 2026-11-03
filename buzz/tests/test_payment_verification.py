from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.base_test_cases import attendee_rows, authorize_payment, create_paid_ticket_type
from buzz.tests.factories import BuzzEventFactory, EventBookingFactory


class TestPaymentVerification(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create()
		cls.ticket_type = create_paid_ticket_type(cls.event.name, 500)

	def setUp(self):
		self.enterContext(self.set_user("Administrator"))
		self.enterContext(patch("frappe.sendmail"))
		self.booking = EventBookingFactory.create(
			event=self.event.name, attendees=attendee_rows(self.ticket_type.name, 1)
		)

	def test_paid_payment_request_confirms_the_booking(self):
		authorize_payment(self.booking)

		self.assertEqual(self.booking.docstatus, 1)
		self.assertEqual(
			frappe.get_last_doc("Event Payment", {"reference_docname": self.booking.name}).payment_received, 1
		)

	def test_refuses_confirmation_without_a_paid_payment_request(self):
		with self.assertRaises(frappe.ValidationError):
			self.booking.on_payment_authorized("Completed")

		self.assertEqual(frappe.db.get_value("Event Booking", self.booking.name, "docstatus"), 0)
