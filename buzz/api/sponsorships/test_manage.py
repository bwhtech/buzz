import frappe

from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.sponsorships import (
	get_event_sponsorship_enquiries,
	get_event_sponsorship_enquiry,
	get_event_sponsorships,
	update_enquiry_status,
)
from buzz.api.sponsorships.exceptions import EnquiryNotFound, EnquiryStatusLocked, EnquiryTierMissing
from buzz.api.sponsorships.test_sponsorships import SponsorshipTestCase

TIER_FIELDS = {"name", "title", "price", "currency", "enabled", "perks", "sponsor_count"}
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
	def make_member(self, team_role: str) -> str:
		email = f"sponsorships-{team_role.lower()}-{frappe.generate_hash(length=6)}@example.com"
		user = frappe.new_doc("User")
		user.email = email
		user.first_name = "Team"
		user.append("roles", {"role": "Buzz User"})
		user.insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Buzz Team Membership",
				"team": self.team(),
				"user": email,
				"team_role": team_role,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
		return email

	def team(self) -> str:
		return frappe.db.get_value("Buzz Event", self.event, "team")


class TestGetEventSponsorships(ManageTestCase):
	def test_team_member_reads_tiers_and_sponsors(self):
		self.make_sponsor()
		frappe.set_user(self.make_member("Manager"))

		response = get_event_sponsorships(self.event)

		self.assertEqual(set(response.tiers[0].__json__()), TIER_FIELDS)
		self.assertEqual(set(response.sponsors[0].__json__()), SPONSOR_FIELDS)

	def test_tier_counts_its_sponsors(self):
		self.make_sponsor()
		frappe.set_user(self.make_member("Manager"))

		response = get_event_sponsorships(self.event)

		tier = next(tier for tier in response.tiers if tier.name == self.tier.name)
		self.assertEqual(tier.sponsor_count, 1)

	def test_non_member_is_refused(self):
		frappe.set_user(self.make_stranger())

		with self.assertRaises(CannotManageEvent):
			get_event_sponsorships(self.event)

	def test_viewer_gets_can_write_false(self):
		frappe.set_user(self.make_member("Viewer"))

		response = get_event_sponsorships(self.event)

		self.assertFalse(response.can_write)


class TestGetEventSponsorshipEnquiries(ManageTestCase):
	def make_enquiry(self, company_name: str, status: str = "Approval Pending"):
		return frappe.get_doc(
			{
				"doctype": "Sponsorship Enquiry",
				"event": self.event,
				"tier": self.tier.name,
				"company_name": company_name,
				"company_logo": "/files/acme.png",
				"status": status,
			}
		).insert()

	def test_rows_carry_tier_title_and_price(self):
		frappe.set_user(self.make_member("Viewer"))

		response = get_event_sponsorship_enquiries(self.event, search="Acme Corp")

		row = next(row for row in response.enquiries if row.name == self.enquiry.name)
		self.assertEqual(set(row.__json__()), ENQUIRY_FIELDS)
		self.assertEqual((row.tier_title, row.tier_price), (self.tier.title, 5000))

	def test_search_and_status_narrow_the_page(self):
		suffix = frappe.generate_hash(length=6)
		paid = self.make_enquiry(f"Zeta {suffix}", status="Paid")
		self.make_enquiry(f"Zeta {suffix} Two")
		frappe.set_user(self.make_member("Manager"))

		response = get_event_sponsorship_enquiries(self.event, search=f"Zeta {suffix}", statuses="Paid")

		self.assertEqual([row.name for row in response.enquiries], [paid.name])
		self.assertEqual(response.matched, 1)
		self.assertGreaterEqual(response.total, 3)

	def test_pages_follow_start_and_limit(self):
		suffix = frappe.generate_hash(length=6)
		for index in range(3):
			self.make_enquiry(f"Paged {suffix} {index}")
		frappe.set_user(self.make_member("Manager"))

		first = get_event_sponsorship_enquiries(self.event, search=f"Paged {suffix}", order="asc", limit=2)
		rest = get_event_sponsorship_enquiries(
			self.event, search=f"Paged {suffix}", order="asc", start=2, limit=2
		)

		self.assertTrue(first.has_next_page)
		self.assertFalse(rest.has_next_page)
		names = [row.company_name for row in first.enquiries + rest.enquiries]
		self.assertEqual(names, [f"Paged {suffix} {index}" for index in range(3)])

	def test_stranger_is_refused(self):
		frappe.set_user(self.make_stranger())

		with self.assertRaises(CannotManageEvent):
			get_event_sponsorship_enquiries(self.event)


class TestGetEventSponsorshipEnquiry(ManageTestCase):
	def test_team_member_reads_answers_and_sponsor(self):
		self.enquiry.append("additional_fields", {"label": "Budget", "fieldname": "budget", "value": "5000"})
		self.enquiry.save()
		sponsor = self.make_sponsor()
		frappe.set_user(self.make_member("Viewer"))

		detail = get_event_sponsorship_enquiry(self.enquiry.name)

		self.assertEqual(detail.sponsor, sponsor.name)
		self.assertEqual([(answer.label, answer.value) for answer in detail.answers], [("Budget", "5000")])

	def test_stranger_is_refused(self):
		frappe.set_user(self.make_stranger())

		with self.assertRaises(CannotManageEvent):
			get_event_sponsorship_enquiry(self.enquiry.name)

	def test_unknown_enquiry_is_not_found(self):
		with self.assertRaises(EnquiryNotFound):
			get_event_sponsorship_enquiry("does-not-exist")


class TestUpdateEnquiryStatus(ManageTestCase):
	def status(self) -> str:
		return frappe.db.get_value("Sponsorship Enquiry", self.enquiry.name, "status")

	def test_manager_moves_the_enquiry_along(self):
		frappe.set_user(self.make_member("Manager"))

		self.assertEqual(update_enquiry_status(self.enquiry.name, "Payment Pending"), "Payment Pending")
		self.assertEqual(self.status(), "Payment Pending")

	def test_marking_paid_lists_the_sponsor_once(self):
		frappe.set_user(self.make_member("Manager"))

		update_enquiry_status(self.enquiry.name, "Paid")
		update_enquiry_status(self.enquiry.name, "Paid")

		self.assertEqual(frappe.db.count("Event Sponsor", {"enquiry": self.enquiry.name}), 1)

	def test_paid_enquiry_keeps_its_status(self):
		frappe.set_user(self.make_member("Manager"))
		update_enquiry_status(self.enquiry.name, "Paid")

		with self.assertRaises(EnquiryStatusLocked):
			update_enquiry_status(self.enquiry.name, "Withdrawn")

	def test_approval_needs_a_tier(self):
		frappe.db.set_value("Sponsorship Enquiry", self.enquiry.name, "tier", None)
		frappe.set_user(self.make_member("Manager"))

		with self.assertRaises(EnquiryTierMissing):
			update_enquiry_status(self.enquiry.name, "Payment Pending")

	def test_unknown_status_is_rejected(self):
		frappe.set_user(self.make_member("Manager"))

		with self.assertRaises(frappe.ValidationError):
			update_enquiry_status(self.enquiry.name, "Rejected")

	def test_viewer_and_stranger_are_refused(self):
		for user in (self.make_member("Viewer"), self.make_stranger()):
			with self.subTest(user):
				frappe.set_user(user)
				with self.assertRaises(CannotManageEvent):
					update_enquiry_status(self.enquiry.name, "Withdrawn")
		frappe.set_user("Administrator")
		self.assertEqual(self.status(), "Approval Pending")
