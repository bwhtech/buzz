import unittest

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.campaigns import get_campaign_details
from buzz.api.exceptions import Conflict
from buzz.utils import is_app_installed


def make_campaign(enabled: int = 1) -> str:
	# Buzz Campaign uses autoname "prompt" -> name set explicitly.
	campaign = frappe.new_doc("Buzz Campaign")
	campaign.name = f"Campaign {frappe.generate_hash(length=6)}"
	campaign.title = campaign.name
	campaign.description = "Interest list for the next edition"
	campaign.enabled = enabled
	campaign.insert(ignore_permissions=True)
	return campaign.name


class TestCampaignErrors(IntegrationTestCase):
	def test_unknown_campaign_raises_not_found(self):
		with self.assertRaises(frappe.DoesNotExistError):
			get_campaign_details("no-such-campaign")

	def test_conflict_maps_to_409(self):
		self.assertEqual(Conflict.http_status_code, 409)


# Buzz Campaign refuses to save unless Frappe CRM is installed.
@unittest.skipUnless(is_app_installed("crm"), "requires the crm app")
class TestGetCampaignDetails(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_returns_expected_keys(self):
		details = get_campaign_details(make_campaign()).__json__()

		self.assertEqual(set(details), {"title", "description", "event"})

	def test_disabled_campaign_raises_conflict(self):
		campaign = make_campaign(enabled=0)

		with self.assertRaises(Conflict):
			get_campaign_details(campaign)
