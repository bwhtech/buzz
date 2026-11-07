from unittest.mock import patch

import frappe
from bwh_payments import testing as payment_testing
from frappe.tests import IntegrationTestCase

from buzz.api.payouts import get_payout_account, refresh_payout_account, submit_payout_account
from buzz.api.payouts.exceptions import (
	InvalidPayoutDetails,
	NotTeamOwner,
	PayoutsNotConfigured,
	PayoutsNotEnabled,
)
from buzz.api.payouts.services import PAYOUTS_FLAG
from buzz.tests.base_test_cases import make_payment_gateway
from buzz.tests.factories import BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory

OWNER = "payout-owner@example.com"
ADMIN = "payout-admin@example.com"
TEST_SAVEPOINT = "payout_test"


def payout_details(**overrides) -> dict:
	return {
		"email": "accounts@team.test",
		"phone": "9000090000",
		"legal_business_name": "Acme Events LLP",
		"business_type": "llp",
		"contact_name": "Asha Rao",
		"category": "media_and_entertainment",
		"subcategory": "ticketing",
		"registered_address": {
			"street1": "12 MG Road",
			"city": "Bengaluru",
			"state": "KARNATAKA",
			"postal_code": "560001",
		},
		"stakeholder_name": "Asha Rao",
		"stakeholder_email": "accounts@team.test",
		"bank_account_number": "50100123456789",
		"ifsc_code": "HDFC0000317",
		"beneficiary_name": "Acme Events LLP",
		"terms_accepted": True,
		**overrides,
	}


class TestPayoutAccount(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Onboarding commits each id the gateway hands back; held so each test can roll back.
		cls.held_commits = payment_testing.without_commits()
		cls.held_commits.__enter__()
		cls.gateway = make_payment_gateway()
		cls.team = BuzzTeamFactory.create_owned_by(UserFactory.create_once(OWNER).name).name
		BuzzTeamMembershipFactory.create(
			team=cls.team, user=UserFactory.create_once(ADMIN).name, team_role="Admin"
		)

	@classmethod
	def tearDownClass(cls):
		cls.held_commits.__exit__(None, None, None)
		super().tearDownClass()

	def setUp(self):
		payment_testing.reset()
		frappe.db.savepoint(TEST_SAVEPOINT)
		self.addCleanup(frappe.db.rollback, save_point=TEST_SAVEPOINT)
		self.enterContext(self.change_settings("Buzz Settings", payout_gateway=self.gateway))
		self.sendmail = self.enterContext(patch("frappe.sendmail"))
		self.enterContext(self.set_user(OWNER))

	def test_a_team_without_an_account_has_no_status(self):
		self.assertEqual(get_payout_account(self.team).__json__(), {"status": None, "requirements": []})

	def test_the_owner_submits_the_teams_payout_account(self):
		account = submit_payout_account(self.team, payout_details())

		self.assertEqual(account.status, "Pending")
		self.assertEqual(account.requirements, [])

	def test_every_owner_is_told_when_the_payout_details_change(self):
		submit_payout_account(self.team, payout_details())

		self.assertEqual(self.sendmail.call_args.kwargs["recipients"], [OWNER])

	def test_an_activated_account_reads_as_active(self):
		submit_payout_account(self.team, payout_details())
		linked_account = frappe.db.get_value("Gateway Linked Account", {"ref_docname": self.team})
		payment_testing.set_linked_account_activation(linked_account, "activated")

		self.assertEqual(refresh_payout_account(self.team).status, "Active")

	def test_what_the_gateway_still_needs_is_shown(self):
		submit_payout_account(self.team, payout_details())
		linked_account = frappe.db.get_value("Gateway Linked Account", {"ref_docname": self.team})
		requirements = [{"field_reference": "settlements.ifsc_code", "reason_code": "field_missing"}]
		payment_testing.set_linked_account_activation(linked_account, "needs_clarification", requirements)

		account = refresh_payout_account(self.team)

		self.assertEqual((account.status, account.requirements), ("Needs Clarification", requirements))

	def test_missing_details_name_the_field(self):
		details = payout_details()
		del details["ifsc_code"]

		with self.assertRaisesRegex(InvalidPayoutDetails, "ifsc_code"):
			submit_payout_account(self.team, details)

	def test_an_admin_cannot_change_where_the_money_goes(self):
		with self.set_user(ADMIN), self.assertRaises(NotTeamOwner):
			submit_payout_account(self.team, payout_details())

	def test_payouts_must_be_enabled_for_the_team(self):
		self.addCleanup(BuzzTeamFactory.set_settings, self.team, {PAYOUTS_FLAG: 1})
		BuzzTeamFactory.set_settings(self.team, {PAYOUTS_FLAG: 0})

		with self.assertRaises(PayoutsNotEnabled):
			get_payout_account(self.team)

	def test_payouts_need_a_payout_gateway_on_the_site(self):
		with (
			self.change_settings("Buzz Settings", payout_gateway=None),
			self.assertRaises(PayoutsNotConfigured),
		):
			get_payout_account(self.team)
