import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.booking.schemas import BookingRequest
from buzz.tests.factories import (
	BuzzEventFactory,
	EventTicketTypeFactory,
	SponsorshipEnquiryFactory,
	SponsorshipTierFactory,
	UserFactory,
)
from buzz.tests.factories.events.event_sponsor_factory import EventSponsorFactory

BOOKER = "booking-owner@example.com"
OUTSIDER = "booking-outsider@example.com"


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
