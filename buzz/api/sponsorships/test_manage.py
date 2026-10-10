import frappe

from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.sponsorships import (
	get_event_sponsorship_enquiries,
	get_event_sponsorship_enquiry,
	get_event_sponsorships,
	update_enquiry_status,
)
from buzz.api.sponsorships.exceptions import EnquiryNotFound, EnquiryStatusLocked, EnquiryTierMissing
from buzz.tests.base_test_cases import SponsorshipTestCase
from buzz.tests.factories import BuzzTeamMembershipFactory, SponsorshipEnquiryFactory, UserFactory

TIER_FIELDS = {"name", "title", "prices", "slots", "enabled", "perks", "sponsor_count"}
SPONSOR_FIELDS = {
	"name",
	"company_name",
	"company_logo",
	"website",
	"country",
	"contact_email",
	"enquiry",
	"tier",
	"tier_title",
	"tags",
}
ENQUIRY_FIELDS = {
	"name",
	"company_name",
	"company_logo",
	"status",
	"tier",
	"tier_title",
	"creation",
	"website",
	"tier_price",
	"tier_currency",
}


class ManageTestCase(SponsorshipTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		team = frappe.db.get_value("Buzz Event", cls.event, "team")
		cls.manager = UserFactory.create_once("sponsorships-manager@example.com").name
		cls.viewer = UserFactory.create_once("sponsorships-viewer@example.com").name
		BuzzTeamMembershipFactory.create(team=team, user=cls.manager, team_role="Manager")
		BuzzTeamMembershipFactory.create(team=team, user=cls.viewer, team_role="Viewer")


class TestGetEventSponsorships(ManageTestCase):
	def test_team_member_reads_tiers_and_sponsors(self):
		self.make_sponsor()

		with self.set_user(self.manager):
			response = get_event_sponsorships(self.event)

		self.assertEqual(set(response.tiers[0].__json__()), TIER_FIELDS)
		self.assertEqual(set(response.sponsors[0].__json__()), SPONSOR_FIELDS)

	def test_tier_counts_its_sponsors(self):
		self.make_sponsor()

		with self.set_user(self.manager):
			response = get_event_sponsorships(self.event)

		tier = next(tier for tier in response.tiers if tier.name == self.tier.name)
		self.assertEqual(tier.sponsor_count, 1)

	def test_non_member_is_refused(self):
		with self.set_user(self.make_stranger()), self.assertRaises(CannotManageEvent):
			get_event_sponsorships(self.event)

	def test_viewer_gets_can_write_false(self):
		with self.set_user(self.viewer):
			response = get_event_sponsorships(self.event)

		self.assertFalse(response.can_write)


class TestGetEventSponsorshipEnquiries(ManageTestCase):
	def test_rows_carry_tier_title_and_price(self):
		with self.set_user(self.viewer):
			response = get_event_sponsorship_enquiries(self.event, search="Acme Corp")

		row = next(row for row in response.enquiries if row.name == self.enquiry.name)
		self.assertEqual(set(row.__json__()), ENQUIRY_FIELDS)
		self.assertEqual((row.tier_title, row.tier_price), ("Gold", 5000))

	def test_search_and_status_narrow_the_page(self):
		suffix = frappe.generate_hash(length=6)
		paid = self.create_enquiry(f"Zeta {suffix}", status="Paid")
		self.create_enquiry(f"Zeta {suffix} Two")

		with self.set_user(self.manager):
			response = get_event_sponsorship_enquiries(
				self.event, search=f"Zeta {suffix}", filters='[["status", "in", ["Paid"]]]'
			)

		self.assertEqual([row.name for row in response.enquiries], [paid.name])
		self.assertEqual(response.matched, 1)
		self.assertGreaterEqual(response.total, 3)

	def test_form_questions_are_offered_and_filter_the_page(self):
		# Every event is created with its enquiry form.
		form = frappe.get_doc("Sponsor Enquiry Form", {"event": self.event})
		form.append("custom_fields", {"label": "Needs a booth", "fieldname": "booth", "fieldtype": "Check"})
		form.save()
		booth = SponsorshipEnquiryFactory.create(
			event=self.event,
			additional_fields=[{"fieldname": "booth", "label": "Needs a booth", "value": "1"}],
		)

		with self.set_user(self.manager):
			response = get_event_sponsorship_enquiries(self.event, filters='[["booth", "in", ["1"]]]')

		self.assertIn("booth", [field.key for field in response.filter_fields])
		self.assertEqual([row.name for row in response.enquiries], [booth.name])

	def test_pages_follow_start_and_limit(self):
		suffix = frappe.generate_hash(length=6)
		for index in range(3):
			self.create_enquiry(f"Paged {suffix} {index}")

		with self.set_user(self.manager):
			search = {"search": f"Paged {suffix}", "order": "asc", "limit": 2}
			first = get_event_sponsorship_enquiries(self.event, **search)
			rest = get_event_sponsorship_enquiries(self.event, start=2, **search)

		self.assertTrue(first.has_next_page)
		self.assertFalse(rest.has_next_page)
		names = [row.company_name for row in first.enquiries + rest.enquiries]
		self.assertEqual(names, [f"Paged {suffix} {index}" for index in range(3)])

	def test_stranger_is_refused(self):
		with self.set_user(self.make_stranger()), self.assertRaises(CannotManageEvent):
			get_event_sponsorship_enquiries(self.event)

	def create_enquiry(self, company_name: str, status: str = "Approval Pending"):
		return SponsorshipEnquiryFactory.create(
			event=self.event, tier=self.tier.name, company_name=company_name, status=status
		)


class TestGetEventSponsorshipEnquiry(ManageTestCase):
	def test_team_member_reads_answers_and_sponsor(self):
		self.enquiry.append("additional_fields", {"label": "Budget", "fieldname": "budget", "value": "5000"})
		self.enquiry.save()
		sponsor = self.make_sponsor()

		with self.set_user(self.viewer):
			detail = get_event_sponsorship_enquiry(self.enquiry.name)

		self.assertEqual(detail.sponsor, sponsor.name)
		self.assertEqual([(answer.label, answer.value) for answer in detail.answers], [("Budget", "5000")])

	def test_stranger_is_refused(self):
		with self.set_user(self.make_stranger()), self.assertRaises(CannotManageEvent):
			get_event_sponsorship_enquiry(self.enquiry.name)

	def test_unknown_enquiry_is_not_found(self):
		with self.assertRaises(EnquiryNotFound):
			get_event_sponsorship_enquiry("does-not-exist")


class TestUpdateEnquiryStatus(ManageTestCase):
	def setUp(self):
		super().setUp()
		self.enterContext(self.set_user(self.manager))

	def test_manager_moves_the_enquiry_along(self):
		self.assertEqual(update_enquiry_status(self.enquiry.name, "Payment Pending"), "Payment Pending")
		self.assertEqual(self.enquiry_status(), "Payment Pending")

	def test_marking_paid_lists_the_sponsor_once(self):
		update_enquiry_status(self.enquiry.name, "Paid")
		update_enquiry_status(self.enquiry.name, "Paid")

		self.assertEqual(frappe.db.count("Event Sponsor", {"enquiry": self.enquiry.name}), 1)

	def test_paid_enquiry_keeps_its_status(self):
		update_enquiry_status(self.enquiry.name, "Paid")

		with self.assertRaises(EnquiryStatusLocked):
			update_enquiry_status(self.enquiry.name, "Withdrawn")

	def test_approval_needs_a_tier(self):
		frappe.db.set_value("Sponsorship Enquiry", self.enquiry.name, "tier", None)

		with self.assertRaises(EnquiryTierMissing):
			update_enquiry_status(self.enquiry.name, "Payment Pending")

	def test_unknown_status_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			update_enquiry_status(self.enquiry.name, "Rejected")

	def test_viewer_and_stranger_are_refused(self):
		for user in (self.viewer, self.make_stranger()):
			with self.subTest(user), self.set_user(user), self.assertRaises(CannotManageEvent):
				update_enquiry_status(self.enquiry.name, "Withdrawn")

		self.assertEqual(self.enquiry_status(), "Approval Pending")

	def enquiry_status(self) -> str:
		return frappe.db.get_value("Sponsorship Enquiry", self.enquiry.name, "status")
