import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.sponsorships import (
	create_sponsorship_payment_link,
	get_sponsorship_details,
	get_user_sponsorship_inquiries,
	withdraw_sponsorship_enquiry,
)
from buzz.api.sponsorships.exceptions import (
	EnquiryAlreadyPaid,
	EnquiryAlreadyWithdrawn,
	EnquiryNotAccessible,
	PaymentNotPermitted,
	WithdrawalNotPermitted,
)

ENQUIRY_FIELDS = {
	"name",
	"company_name",
	"company_logo",
	"event",
	"tier",
	"tier_title",
	"status",
	"creation",
	"owner",
}
EVENT_FIELDS = {"title", "short_description", "about", "start_date", "end_date", "venue", "route"}
SPONSOR_FIELDS = {"name", "company_name", "company_logo", "creation", "event", "tier", "tier_title"}
LIST_FIELDS = {
	"name",
	"company_name",
	"event",
	"tier",
	"status",
	"creation",
	"event_title",
	"tier_title",
	"has_sponsor",
}


class SponsorshipTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = str(frappe.get_doc("Buzz Event", {"route": "test-route"}).name)

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.clear_messages()

		self.tier = frappe.get_doc(
			{
				"doctype": "Sponsorship Tier",
				"event": self.event,
				"title": f"Sponsorship Test {frappe.generate_hash(length=6)}",
				"price": 5000,
				"currency": "INR",
			}
		).insert()

		self.enquiry = frappe.get_doc(
			{
				"doctype": "Sponsorship Enquiry",
				"event": self.event,
				"tier": self.tier.name,
				"company_name": "Acme Corp",
				"company_logo": "/files/acme.png",
				"status": "Approval Pending",
			}
		).insert()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def make_stranger(self) -> str:
		email = f"stranger-{frappe.generate_hash(length=6)}@example.com"
		user = frappe.new_doc("User")
		user.email = email
		user.first_name = "Stranger"
		user.append("roles", {"role": "Buzz User"})
		user.insert(ignore_permissions=True)
		return email

	def make_sponsor(self):
		return frappe.get_doc(
			{
				"doctype": "Event Sponsor",
				"event": self.event,
				"tier": self.tier.name,
				"company_name": "Acme Corp",
				"company_logo": "/files/acme.png",
				"enquiry": self.enquiry.name,
			}
		).insert()


class TestGetSponsorshipDetails(SponsorshipTestCase):
	def test_response_shape(self):
		response = get_sponsorship_details(self.enquiry.name).__json__()

		self.assertEqual(set(response), {"enquiry", "event_details", "sponsor_details", "has_sponsor"})
		self.assertEqual(set(response["enquiry"]), ENQUIRY_FIELDS)
		self.assertEqual(set(response["event_details"]), EVENT_FIELDS)

	def test_enquiry_carries_the_tier_title(self):
		enquiry = get_sponsorship_details(self.enquiry.name).__json__()["enquiry"]

		self.assertEqual(enquiry["name"], self.enquiry.name)
		self.assertEqual(enquiry["tier_title"], self.tier.title)
		self.assertEqual(enquiry["owner"], "Administrator")

	def test_no_sponsor_yet(self):
		response = get_sponsorship_details(self.enquiry.name).__json__()

		self.assertFalse(response["has_sponsor"])
		self.assertIsNone(response["sponsor_details"])

	def test_sponsor_details_once_sponsored(self):
		sponsor = self.make_sponsor()
		response = get_sponsorship_details(self.enquiry.name).__json__()

		self.assertTrue(response["has_sponsor"])
		self.assertEqual(set(response["sponsor_details"]), SPONSOR_FIELDS)
		self.assertEqual(response["sponsor_details"]["name"], sponsor.name)
		self.assertEqual(response["sponsor_details"]["tier_title"], self.tier.title)

	def test_stranger_is_refused(self):
		frappe.set_user(self.make_stranger())

		with self.assertRaises(EnquiryNotAccessible):
			get_sponsorship_details(self.enquiry.name)

		self.assertEqual(frappe.local.message_log[-1]["title"], "Not Permitted")

	def test_unknown_enquiry_raises_does_not_exist(self):
		with self.assertRaises(frappe.DoesNotExistError):
			get_sponsorship_details("no-such-enquiry")

	def test_status_codes(self):
		self.assertEqual(EnquiryNotAccessible.http_status_code, 403)
		self.assertEqual(PaymentNotPermitted.http_status_code, 403)
		self.assertEqual(WithdrawalNotPermitted.http_status_code, 403)
		self.assertEqual(EnquiryAlreadyPaid.http_status_code, 409)
		self.assertEqual(EnquiryAlreadyWithdrawn.http_status_code, 409)


class TestGetUserSponsorshipInquiries(SponsorshipTestCase):
	def test_response_shape(self):
		rows = [row.__json__() for row in get_user_sponsorship_inquiries()]
		mine = [row for row in rows if row["name"] == self.enquiry.name]

		self.assertEqual(len(mine), 1)
		self.assertEqual(set(mine[0]), LIST_FIELDS)
		self.assertEqual(mine[0]["tier_title"], self.tier.title)
		self.assertEqual(mine[0]["event_title"], frappe.db.get_value("Buzz Event", self.event, "title"))
		self.assertFalse(mine[0]["has_sponsor"])

	def test_has_sponsor_flips_once_sponsored(self):
		self.make_sponsor()
		rows = {row.name: row for row in get_user_sponsorship_inquiries()}

		self.assertTrue(rows[self.enquiry.name].has_sponsor)

	def test_only_own_enquiries_are_listed(self):
		frappe.set_user(self.make_stranger())

		names = [row.name for row in get_user_sponsorship_inquiries()]

		self.assertNotIn(self.enquiry.name, names)


class TestWithdrawSponsorshipEnquiry(SponsorshipTestCase):
	def test_withdraw_sets_the_status(self):
		withdraw_sponsorship_enquiry(self.enquiry.name)

		self.assertEqual(frappe.db.get_value("Sponsorship Enquiry", self.enquiry.name, "status"), "Withdrawn")

	def test_second_withdrawal_is_rejected(self):
		withdraw_sponsorship_enquiry(self.enquiry.name)
		frappe.clear_messages()

		with self.assertRaises(EnquiryAlreadyWithdrawn):
			withdraw_sponsorship_enquiry(self.enquiry.name)

		self.assertEqual(frappe.local.message_log[-1]["title"], "Already Withdrawn")

	def test_paid_enquiry_cannot_be_withdrawn(self):
		frappe.db.set_value("Sponsorship Enquiry", self.enquiry.name, "status", "Paid")
		frappe.clear_document_cache("Sponsorship Enquiry", self.enquiry.name)

		with self.assertRaises(EnquiryAlreadyPaid):
			withdraw_sponsorship_enquiry(self.enquiry.name)

	def test_stranger_cannot_withdraw(self):
		frappe.set_user(self.make_stranger())

		with self.assertRaises(WithdrawalNotPermitted):
			withdraw_sponsorship_enquiry(self.enquiry.name)


class TestCreateSponsorshipPaymentLink(SponsorshipTestCase):
	def test_stranger_cannot_create_a_payment_link(self):
		frappe.set_user(self.make_stranger())

		with self.assertRaises(PaymentNotPermitted):
			create_sponsorship_payment_link(self.enquiry.name, self.tier.name)
