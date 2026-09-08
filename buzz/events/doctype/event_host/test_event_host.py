# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.forms.test_forms import ensure_prompt_named_record
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team
from buzz.patches.backfill_event_co_hosts import execute as backfill_event_co_hosts
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

	def make_event(self, team: str, host: str) -> str:
		event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": f"Backfill Event {frappe.generate_hash(length=6)}",
				"team": team,
				"category": ensure_prompt_named_record("Event Category", "Test Category"),
				"host": host,
				"start_date": "2030-01-01",
				"start_time": "09:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
			}
		)
		event.insert(ignore_permissions=True)
		return event.name

	def test_backfill_carries_a_legacy_host_into_the_co_host_table(self):
		team = create_owned_team(f"Backfill Team {frappe.generate_hash(length=6)}", "Administrator")
		host = frappe.get_doc({"doctype": "Event Host", "host_name": "Acme Corp", "team": team}).insert(
			ignore_permissions=True
		)
		event = self.make_event(team, host.name)
		frappe.db.delete("Event CoHost", {"parent": event})

		backfill_event_co_hosts()

		self.assertEqual(frappe.get_all("Event CoHost", filters={"parent": event}, pluck="host"), [host.name])

	def test_backfill_skips_a_host_named_after_its_own_team(self):
		name = f"Minted Team {frappe.generate_hash(length=6)}"
		team = create_owned_team(name, "Administrator")
		host = frappe.get_doc({"doctype": "Event Host", "host_name": name, "team": team}).insert(
			ignore_permissions=True
		)
		event = self.make_event(team, host.name)
		frappe.db.delete("Event CoHost", {"parent": event})

		backfill_event_co_hosts()

		self.assertEqual(frappe.get_all("Event CoHost", filters={"parent": event}, pluck="host"), [])
