import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.tags import set_tags
from buzz.patches.migrate_desk_tags_to_buzz_tags import execute
from buzz.tests.factories import BuzzEventFactory, BuzzTagFactory, EventSponsorFactory


class TestMigrateDeskTagsToBuzzTags(IntegrationTestCase):
	def test_frappe_tags_become_team_tags_alongside_existing_ones(self):
		event = BuzzEventFactory.create()
		sponsor = EventSponsorFactory.create(event=event.name).name
		kept = BuzzTagFactory.create(team=event.team, label=f"Gold {frappe.generate_hash(length=8)}")
		set_tags("Event Sponsor", sponsor, [kept.name])
		desk_label = f"Returning {frappe.generate_hash(length=8)}"
		frappe.db.set_value("Event Sponsor", sponsor, "_user_tags", f"{kept.label},{desk_label} ,")

		execute()

		labels = sorted([kept.label, desk_label])
		migrated = frappe.get_all(
			"Buzz Tag", {"team": event.team, "label": ["in", labels]}, pluck="label", order_by="label"
		)
		self.assertEqual(migrated, labels)
		self.assertEqual(frappe.db.count("Buzz Tag Link", {"document_name": sponsor}), 2)
		self.assertEqual(frappe.db.get_value("Event Sponsor", sponsor, "_user_tags"), ",".join(labels))
