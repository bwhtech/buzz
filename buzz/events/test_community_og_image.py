import io
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today
from PIL import Image

from buzz.events.community_og_image import CommunityOgImage, generate
from buzz.events.doctype.buzz_team.team_page import TeamPage
from buzz.events.og_image import clear
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, CommunityEventRequestFactory


class TestCommunityOgImage(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.team = BuzzTeamFactory.create_owned_by(team_name="Share Image Builders", is_published=1).name

	def tearDown(self):
		# Removes the rendered files from disk too, which a rollback leaves behind
		clear(frappe.get_doc("Buzz Team", self.team))

	def create_event(self, offset: int, **overrides):
		day = add_days(today(), offset)
		return BuzzEventFactory.create(team=self.team, start_date=day, end_date=day, **overrides)

	def image(self) -> CommunityOgImage:
		return CommunityOgImage(frappe.get_doc("Buzz Team", self.team))

	def test_renders_a_share_sized_png(self):
		content = self.image().render()
		self.assertEqual(Image.open(io.BytesIO(content)).size, (1200, 630))

	def test_a_team_with_nothing_to_count_has_no_stats(self):
		self.assertEqual(self.image().stats, [])

	def test_counts_match_the_page(self):
		self.create_event(7)
		self.create_event(-7)
		page = TeamPage(frappe.get_doc("Buzz Team", self.team))
		counts = [number for number, _label in self.image().stats]

		self.assertEqual(counts, [page.upcoming_count, page.hosted_count])
		self.assertEqual(page.as_context()["events_hosted"], page.hosted_count)

	def test_an_approved_external_event_is_counted(self):
		team = BuzzTeamFactory.create_owned_by(None, "community", team_name="Counted Builders").name
		CommunityEventRequestFactory.create("approved", community=team)

		self.assertEqual(CommunityOgImage(frappe.get_doc("Buzz Team", team)).stats[1][0], 1)

	def test_unchanged_team_keeps_its_image(self):
		self.create_event(7)
		generate(self.team)
		first = self.og_image()
		generate(self.team)

		self.assertEqual((self.og_image(), self.og_files()), (first, [first]))

	def test_changed_name_replaces_the_image(self):
		generate(self.team)
		first = self.og_image()
		frappe.db.set_value("Buzz Team", self.team, "team_name", "Renamed Builders")
		generate(self.team)

		self.assertNotEqual(self.og_image(), first)
		self.assertEqual(self.og_files(), [self.og_image()])

	def test_a_private_team_has_no_image(self):
		generate(self.team)
		frappe.db.set_value("Buzz Team", self.team, "is_published", 0)
		generate(self.team)

		self.assertIsNone(self.og_image())
		self.assertEqual(self.og_files(), [])

	def test_undrawable_name_clears_the_image(self):
		generate(self.team)
		frappe.db.set_value("Buzz Team", self.team, "team_name", "फ्रैपे यात्रा")
		generate(self.team)

		self.assertIsNone(self.og_image())

	def test_saving_a_published_team_queues_a_render(self):
		team = frappe.get_doc("Buzz Team", self.team)
		with patch("frappe.in_test", False), patch("frappe.enqueue") as enqueue:
			team.save()
		queued = {call.kwargs["team_name"] for call in enqueue.call_args_list if "team_name" in call.kwargs}
		self.assertEqual(queued, {self.team})

	def test_a_deleted_team_is_skipped(self):
		generate("Deleted Builders")

	def test_a_logo_that_fails_to_load_keeps_the_current_image(self):
		generate(self.team)
		first = self.og_image()
		frappe.db.set_value("Buzz Team", self.team, "logo", "/files/missing-logo.png")
		generate(self.team)

		self.assertEqual(self.og_image(), first)

	def test_an_external_logo_is_drawn_as_a_monogram(self):
		frappe.db.set_value("Buzz Team", self.team, "logo", "https://example.com/logo.png")
		generate(self.team)

		self.assertIsNotNone(self.og_image())

	def test_a_community_request_move_queues_both_communities(self):
		first = BuzzTeamFactory.create_owned_by(
			None, "community", team_name="First Community", is_published=1
		).name
		other = BuzzTeamFactory.create_owned_by(
			None, "community", team_name="Next Community", is_published=1
		).name
		request = CommunityEventRequestFactory.create("approved", community=first)
		request.community = other
		with patch("frappe.in_test", False), patch("frappe.enqueue") as enqueue:
			request.save()

		queued = {call.kwargs["team_name"] for call in enqueue.call_args_list}
		self.assertEqual(queued, {first, other})

	def og_image(self) -> str:
		return frappe.db.get_value("Buzz Team", self.team, "og_image")

	def og_files(self) -> list:
		return frappe.get_all(
			"File",
			filters={"attached_to_name": self.team, "attached_to_field": "og_image"},
			pluck="file_url",
		)
