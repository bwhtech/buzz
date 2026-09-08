# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.patches.backfill_event_host_names import execute as backfill_event_host_names

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestEventHost(IntegrationTestCase):
	"""
	Integration tests for EventHost.
	Use this class for testing interactions between multiple components.
	"""

	def make_legacy_host(self) -> str:
		"""A host from before `host_name` existed: the docname was the label."""
		host = frappe.get_doc({"doctype": "Event Host", "host_name": "Legacy Host"}).insert(
			ignore_permissions=True
		)
		frappe.db.set_value("Event Host", host.name, "host_name", "", update_modified=False)
		return host.name

	def test_backfill_names_a_host_that_has_none(self):
		host = self.make_legacy_host()

		backfill_event_host_names()

		self.assertEqual(frappe.db.get_value("Event Host", host, "host_name"), host)

	def test_backfill_leaves_a_named_host_alone(self):
		host = frappe.get_doc({"doctype": "Event Host", "host_name": "Acme Corp"}).insert(
			ignore_permissions=True
		)

		backfill_event_host_names()

		self.assertEqual(frappe.db.get_value("Event Host", host.name, "host_name"), "Acme Corp")
