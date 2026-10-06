import unittest

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.campaigns import get_campaign_details
from buzz.api.campaigns.exceptions import CampaignNotActive
from buzz.tests.factories.events.buzz_campaign_factory import BuzzCampaignFactory
from buzz.utils import is_app_installed


class TestCampaignErrors(IntegrationTestCase):
	def test_unknown_campaign_raises_not_found(self):
		with self.assertRaises(frappe.DoesNotExistError):
			get_campaign_details("no-such-campaign")


# Buzz Campaign refuses to save unless Frappe CRM is installed.
@unittest.skipUnless(is_app_installed("crm"), "requires the crm app")
class TestGetCampaignDetails(IntegrationTestCase):
	def test_disabled_campaign_reports_its_message(self):
		campaign = BuzzCampaignFactory.create(enabled=0).name
		frappe.clear_messages()

		with self.assertRaises(CampaignNotActive):
			get_campaign_details(campaign)

		self.assertEqual(frappe.local.message_log[-1]["title"], "Campaign Closed")
