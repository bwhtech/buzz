# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestEventSponsor(IntegrationTestCase):
	"""
	Integration tests for EventSponsor.
	Use this class for testing interactions between multiple components.
	"""

	def test_enquiry_to_sponsor_flow(self):
		test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		test_sponsorship_tier = frappe.get_doc(
			{
				"doctype": "Sponsorship Tier",
				"event": test_event.name,
				"title": "Super Platinum",
				"prices": [{"currency": "INR", "price": 1000}],
			}
		).insert()

		test_enquiry = frappe.get_doc(
			{
				"doctype": "Sponsorship Enquiry",
				"event": test_event.name,
				"company_name": "Test Studios",
				"company_logo": "https://buildwithhussain.com/files/youtube2.png",
				"tier": test_sponsorship_tier.name,
			}
		).insert()

		# "Payment Success trigger"
		test_enquiry.on_payment_authorized("Completed")
		self.assertEqual(test_enquiry.status, "Paid")

		self.assertTrue(frappe.db.exists("Event Sponsor", {"enquiry": test_enquiry.name}))
