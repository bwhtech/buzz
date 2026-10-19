# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.uninstall import before_uninstall


class TestUninstall(IntegrationTestCase):
	def test_uninstall_removes_the_user_invitation_fields(self):
		before_uninstall()

		for fieldname in ("buzz_team", "buzz_team_role"):
			self.assertFalse(
				frappe.db.exists("Custom Field", {"dt": "User Invitation", "fieldname": fieldname})
			)
