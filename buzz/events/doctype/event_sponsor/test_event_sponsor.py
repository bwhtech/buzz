# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import SponsorshipEnquiryFactory, SponsorshipTierFactory


class IntegrationTestEventSponsor(IntegrationTestCase):
	def test_paid_gateway_callback_lists_the_sponsor(self):
		tier = SponsorshipTierFactory.create()
		enquiry = SponsorshipEnquiryFactory.create(event=tier.event, tier=tier.name)

		enquiry.on_payment_authorized("Completed")

		self.assertEqual(enquiry.status, "Paid")
		self.assertTrue(frappe.db.exists("Event Sponsor", {"enquiry": enquiry.name}))
