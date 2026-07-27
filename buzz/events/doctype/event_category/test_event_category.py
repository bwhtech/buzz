# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.utils import ZOOM_BACKED_CATEGORIES


class IntegrationTestEventCategory(IntegrationTestCase):
	def test_zoom_backed_categories_are_seeded(self):
		for category in ZOOM_BACKED_CATEGORIES:
			self.assertTrue(frappe.db.exists("Event Category", category), category)
