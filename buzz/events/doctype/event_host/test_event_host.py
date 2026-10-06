# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.patches.backfill_event_co_hosts import execute as backfill_event_co_hosts
from buzz.patches.backfill_event_host_names import execute as backfill_event_host_names
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, EventHostFactory


class IntegrationTestEventHost(IntegrationTestCase):
	def test_backfill_names_a_host_that_has_none(self):
		host = EventHostFactory.create().name
		# A host from before `host_name` existed: the docname was the label.
		frappe.db.set_value("Event Host", host, "host_name", "", update_modified=False)

		backfill_event_host_names()

		self.assertEqual(frappe.db.get_value("Event Host", host, "host_name"), host)

	def test_backfill_leaves_a_named_host_alone(self):
		host = EventHostFactory.create(host_name="Acme Corp").name

		backfill_event_host_names()

		self.assertEqual(frappe.db.get_value("Event Host", host, "host_name"), "Acme Corp")

	def test_backfill_carries_a_legacy_host_into_the_co_host_table(self):
		team = BuzzTeamFactory.create_owned_by().name
		host = EventHostFactory.create(team=team, host_name="Acme Corp").name
		event = self.create_event_without_co_hosts(team, host)

		backfill_event_co_hosts()

		self.assertEqual(frappe.get_all("Event CoHost", filters={"parent": event}, pluck="host"), [host])

	def test_backfill_skips_a_host_named_after_its_own_team(self):
		team_name = f"Minted Team {frappe.generate_hash(length=6)}"
		team = BuzzTeamFactory.create_owned_by(team_name=team_name).name
		host = EventHostFactory.create(team=team, host_name=team_name).name
		event = self.create_event_without_co_hosts(team, host)

		backfill_event_co_hosts()

		self.assertEqual(frappe.get_all("Event CoHost", filters={"parent": event}, pluck="host"), [])

	def create_event_without_co_hosts(self, team: str, host: str) -> str:
		event = str(BuzzEventFactory.create(team=team, host=host).name)
		frappe.db.delete("Event CoHost", {"parent": event})
		return event
