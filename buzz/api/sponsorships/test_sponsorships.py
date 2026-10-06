from unittest.mock import MagicMock, patch

import frappe

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
from buzz.tests.base_test_cases import SponsorshipTestCase
from buzz.tests.factories import PaymentGatewayFactory


class TestGetSponsorshipDetails(SponsorshipTestCase):
	def test_enquiry_carries_the_tier_title(self):
		enquiry = get_sponsorship_details(self.enquiry.name).__json__()["enquiry"]

		self.assertEqual(enquiry["name"], self.enquiry.name)
		self.assertEqual(enquiry["tier_title"], "Gold")
		self.assertEqual(enquiry["owner"], "Administrator")

	def test_no_sponsor_yet(self):
		response = get_sponsorship_details(self.enquiry.name).__json__()

		self.assertFalse(response["has_sponsor"])
		self.assertIsNone(response["sponsor_details"])

	def test_sponsor_details_once_sponsored(self):
		sponsor = self.make_sponsor()
		response = get_sponsorship_details(self.enquiry.name).__json__()

		self.assertTrue(response["has_sponsor"])
		self.assertEqual(
			set(response["sponsor_details"]),
			{"name", "company_name", "company_logo", "creation", "event", "tier", "tier_title"},
		)
		self.assertEqual(response["sponsor_details"]["name"], sponsor.name)
		self.assertEqual(response["sponsor_details"]["tier_title"], "Gold")

	def test_stranger_is_refused(self):
		with self.set_user(self.make_stranger()), self.assertRaises(EnquiryNotAccessible):
			get_sponsorship_details(self.enquiry.name)

		self.assertEqual(frappe.local.message_log[-1]["title"], "Not Permitted")

	def test_unknown_enquiry_raises_does_not_exist(self):
		with self.assertRaises(frappe.DoesNotExistError):
			get_sponsorship_details("no-such-enquiry")


class TestGetUserSponsorshipInquiries(SponsorshipTestCase):
	def test_has_sponsor_flips_once_sponsored(self):
		event_title = frappe.db.get_value("Buzz Event", self.event, "title")
		row = self.listed_row()
		self.assertEqual((row.tier_title, row.event_title, row.has_sponsor), ("Gold", event_title, False))

		self.make_sponsor()

		self.assertTrue(self.listed_row().has_sponsor)

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

		with patch("buzz.payments.get_controller", return_value=MagicMock()):
			create_sponsorship_payment_link(self.enquiry.name, self.tier.name, gateway, currency="USD")

		payment = frappe.get_last_doc("Event Payment", {"reference_docname": self.enquiry.name})
		self.assertEqual((payment.currency, payment.amount), ("USD", 60))

	def test_link_refuses_a_currency_the_tier_has_no_price_in(self):
		gateway = self.add_gateway_to_event()

		with self.assertRaises(frappe.ValidationError):
			create_sponsorship_payment_link(self.enquiry.name, self.tier.name, gateway, currency="EUR")

	def add_gateway_to_event(self) -> str:
		gateway = PaymentGatewayFactory.create().name
		event = frappe.get_doc("Buzz Event", self.event)
		event.set("payment_gateways", [{"payment_gateway": gateway}])
		event.save(ignore_permissions=True)
		self.addCleanup(frappe.clear_document_cache, "Buzz Event", self.event)
		return gateway
