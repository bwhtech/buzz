import frappe
from bwh_payments import testing as payment_testing

from buzz.api.sponsorships import (
	create_sponsorship_payment_link,
	get_user_sponsorship_inquiries,
	update_sponsorship_logo,
	withdraw_sponsorship_enquiry,
)
from buzz.api.sponsorships.exceptions import (
	EnquiryAlreadyPaid,
	EnquiryAlreadyWithdrawn,
	EnquiryLogoLocked,
	LogoChangeNotPermitted,
	PaymentNotPermitted,
	WithdrawalNotPermitted,
)
from buzz.tests.base_test_cases import SponsorshipTestCase, make_payment_gateway
from buzz.tests.factories import BuzzEventFactory, SponsorshipTierFactory


class TestGetUserSponsorshipInquiries(SponsorshipTestCase):
	def test_has_sponsor_flips_once_sponsored(self):
		event_title = frappe.db.get_value("Buzz Event", self.event, "title")
		row = self.listed_row()
		self.assertEqual((row.tier_title, row.event_title, row.has_sponsor), ("Gold", event_title, False))

		self.make_sponsor()

		self.assertTrue(self.listed_row().has_sponsor)

	def test_row_carries_the_tier_price_and_event_date(self):
		start_date = frappe.db.get_value("Buzz Event", self.event, "start_date")
		row = self.listed_row()

		self.assertEqual((row.tier_price, row.tier_currency), (5000, "INR"))
		self.assertEqual(row.start_date, start_date)

	def test_confirmed_sponsor_logo_replaces_the_enquiry_logo(self):
		sponsor = self.make_sponsor()
		frappe.db.set_value("Event Sponsor", sponsor.name, "company_logo", "/files/acme-sponsor.png")
		row = self.listed_row()

		self.assertEqual((row.sponsor, row.company_logo), (sponsor.name, "/files/acme-sponsor.png"))

	def test_only_own_enquiries_are_listed(self):
		with self.set_user(self.make_stranger()):
			names = [row.name for row in get_user_sponsorship_inquiries()]

		self.assertNotIn(self.enquiry.name, names)

	def listed_row(self):
		return next(row for row in get_user_sponsorship_inquiries() if row.name == self.enquiry.name)


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

	def test_applicant_who_is_not_on_the_team_can_withdraw(self):
		applicant = self.make_applicant()

		with self.set_user(applicant):
			withdraw_sponsorship_enquiry(self.enquiry.name)

		self.assertEqual(frappe.db.get_value("Sponsorship Enquiry", self.enquiry.name, "status"), "Withdrawn")

	def test_stranger_cannot_withdraw(self):
		with self.set_user(self.make_stranger()), self.assertRaises(WithdrawalNotPermitted):
			withdraw_sponsorship_enquiry(self.enquiry.name)


class TestCreateSponsorshipPaymentLink(SponsorshipTestCase):
	def test_stranger_cannot_create_a_payment_link(self):
		with self.set_user(self.make_stranger()), self.assertRaises(PaymentNotPermitted):
			create_sponsorship_payment_link(self.enquiry.name, self.tier.name)

	def test_disabled_tier_cannot_create_a_payment_link(self):
		self.tier.enabled = 0
		self.tier.save()

		with self.assertRaises(frappe.ValidationError):
			create_sponsorship_payment_link(self.enquiry.name, self.tier.name)

	def test_link_charges_the_chosen_currency(self):
		self.tier.append("prices", {"currency": "USD", "price": 60})
		self.tier.save()
		gateway = self.add_gateway_to_event()

		create_sponsorship_payment_link(self.enquiry.name, self.tier.name, gateway, currency="USD")

		payment = frappe.get_last_doc("Event Payment", {"reference_docname": self.enquiry.name})
		self.assertEqual((payment.currency, payment.amount), ("USD", 60))

	def test_link_refuses_a_currency_the_tier_has_no_price_in(self):
		gateway = self.add_gateway_to_event()

		with self.assertRaises(frappe.ValidationError):
			create_sponsorship_payment_link(self.enquiry.name, self.tier.name, gateway, currency="EUR")

	def test_paying_the_link_makes_the_enquirer_a_sponsor(self):
		gateway = self.add_gateway_to_event()
		create_sponsorship_payment_link(self.enquiry.name, self.tier.name, gateway)
		payment = frappe.get_last_doc("Event Payment", {"reference_docname": self.enquiry.name})

		payment_testing.pay(payment.payment_request)

		self.assertEqual(frappe.db.get_value("Sponsorship Enquiry", self.enquiry.name, "status"), "Paid")
		self.assertTrue(frappe.db.exists("Event Sponsor", {"enquiry": self.enquiry.name}))
		self.assertEqual(frappe.db.get_value("Event Payment", payment.name, "payment_received"), 1)

	def test_link_refuses_a_tier_from_another_event(self):
		other_event = str(BuzzEventFactory.create().name)
		gateway = self.add_gateway_to_event(other_event)
		other_event_tier = SponsorshipTierFactory.create(event=other_event)

		with self.assertRaises(frappe.ValidationError):
			create_sponsorship_payment_link(self.enquiry.name, other_event_tier.name, gateway)

		self.assertEqual(self.saved_tier(), self.tier.name)

	def test_link_refuses_to_repoint_a_paid_enquiry(self):
		gateway = self.add_gateway_to_event()
		create_sponsorship_payment_link(self.enquiry.name, self.tier.name, gateway)
		payment = frappe.get_last_doc("Event Payment", {"reference_docname": self.enquiry.name})
		payment_testing.pay(payment.payment_request)
		frappe.clear_document_cache("Sponsorship Enquiry", self.enquiry.name)
		cheaper_tier = SponsorshipTierFactory.create(
			event=self.event, title="Silver", prices=[{"currency": "INR", "price": 100}]
		)

		with self.assertRaises(frappe.ValidationError):
			create_sponsorship_payment_link(self.enquiry.name, cheaper_tier.name, gateway)

		self.assertEqual(self.saved_tier(), self.tier.name)

	def test_link_writes_the_tier_once_it_validates(self):
		gateway = self.add_gateway_to_event()
		silver = SponsorshipTierFactory.create(
			event=self.event, title="Silver", prices=[{"currency": "INR", "price": 100}]
		)

		create_sponsorship_payment_link(self.enquiry.name, silver.name, gateway)

		self.assertEqual(self.saved_tier(), silver.name)

	def test_the_sponsor_comes_back_to_their_enquiry_after_paying(self):
		gateway = self.add_gateway_to_event()

		create_sponsorship_payment_link(self.enquiry.name, self.tier.name, gateway)

		payment = frappe.get_last_doc("Event Payment", {"reference_docname": self.enquiry.name})
		self.assertEqual(
			frappe.db.get_value("Gateway Payment Request", payment.payment_request, "redirect_to"),
			f"/b/manage/sponsorship?enquiry={self.enquiry.name}&success=true",
		)

	def saved_tier(self) -> str:
		return frappe.db.get_value("Sponsorship Enquiry", self.enquiry.name, "tier")

	def add_gateway_to_event(self, event: str | None = None) -> str:
		gateway = make_payment_gateway()
		event_name = event or self.event
		event_doc = frappe.get_doc("Buzz Event", event_name)
		event_doc.set("payment_gateways", [{"payment_gateway": gateway}])
		event_doc.save(ignore_permissions=True)
		self.addCleanup(frappe.clear_document_cache, "Buzz Event", event_name)
		return gateway


class TestUpdateSponsorshipLogo(SponsorshipTestCase):
	def test_applicant_changes_the_logo_on_their_open_enquiry(self):
		with self.set_user(self.make_applicant()):
			update_sponsorship_logo(self.enquiry.name, "/files/new-logo.png")

		self.assertEqual(self.saved_logo(), "/files/new-logo.png")

	def test_stranger_cannot_change_the_logo(self):
		with self.set_user(self.make_stranger()), self.assertRaises(LogoChangeNotPermitted):
			update_sponsorship_logo(self.enquiry.name, "/files/new-logo.png")

	def test_logo_is_locked_once_the_enquiry_is_paid(self):
		frappe.db.set_value("Sponsorship Enquiry", self.enquiry.name, "status", "Paid")
		frappe.clear_document_cache("Sponsorship Enquiry", self.enquiry.name)

		with self.set_user(self.make_applicant()), self.assertRaises(EnquiryLogoLocked):
			update_sponsorship_logo(self.enquiry.name, "/files/new-logo.png")

	def saved_logo(self) -> str:
		return frappe.db.get_value("Sponsorship Enquiry", self.enquiry.name, "company_logo")
