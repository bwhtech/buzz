import io
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from PIL import Image

from buzz.events.doctype.buzz_team.buzz_team import create_personal_team_for
from buzz.events.og_image import clear
from buzz.events.profile_og_image import ProfileOgImage, generate, profile_owner
from buzz.tests.factories import BuzzEventFactory, UserFactory
from buzz.www.user_profile import ProfilePage, get_profile_team, get_user_by_username

BIO = "Hosts reading circles."


class TestProfileOgImage(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.user = UserFactory.create_once("profile-image-host@example.com").name
		cls.team = create_personal_team_for(cls.user).name
		cls.event = str(BuzzEventFactory.create(team=cls.team).name)

	def setUp(self):
		self.enterContext(self.change_settings("Buzz Settings", enable_personal_teams=1))
		# Set together: User.validate rebuilds full_name from the other two
		frappe.db.set_value(
			"User",
			self.user,
			{"first_name": "Noor", "last_name": "Host", "full_name": "Noor Host", "bio": BIO},
		)

	def tearDown(self):
		# Removes the rendered files from disk too, which a rollback leaves behind
		clear(self.team_doc())

	def test_renders_a_share_sized_png(self):
		content = self.image().render()
		self.assertEqual(Image.open(io.BytesIO(content)).size, (1200, 630))

	def test_subtitle_names_the_handle_and_hosted_count(self):
		username = frappe.db.get_value("User", self.user, "username")
		self.assertEqual(self.image().subtitle, f"@{username} · 1 event hosted")

	def test_profile_page_shares_the_image_as_a_large_card(self):
		generate(self.team)
		user = get_user_by_username(frappe.db.get_value("User", self.user, "username"))
		meta = ProfilePage(user, get_profile_team(user)).as_context()["meta"]

		self.assertTrue(meta["image"].endswith(self.og_image()))
		self.assertEqual(meta["card"], "summary_large_image")

	def test_unchanged_profile_keeps_its_image(self):
		generate(self.team)
		first = self.og_image()
		generate(self.team)

		self.assertEqual((self.og_image(), self.og_files()), (first, [first]))

	def test_changed_bio_replaces_the_image(self):
		generate(self.team)
		first = self.og_image()
		frappe.db.set_value("User", self.user, "bio", "Runs the Sunday book club.")
		generate(self.team)

		self.assertNotEqual(self.og_image(), first)
		self.assertEqual(self.og_files(), [self.og_image()])

	def test_undrawable_bio_is_left_out(self):
		frappe.db.set_value("User", self.user, "bio", "पुस्तक मंडली")
		image = self.image()

		self.assertEqual(image.bio(), "")
		self.assertTrue(image.can_render())

	def test_a_hidden_profile_has_no_image(self):
		generate(self.team)
		frappe.db.set_value("Buzz Event", self.event, "is_published", 0)
		self.addCleanup(frappe.db.set_value, "Buzz Event", self.event, "is_published", 1)
		generate(self.team)

		self.assertIsNone(self.og_image())
		self.assertEqual(self.og_files(), [])

	def test_no_image_while_personal_teams_are_off(self):
		with self.change_settings("Buzz Settings", enable_personal_teams=0):
			self.assertIsNone(profile_owner(self.team_doc()))

	def test_saving_the_owner_queues_a_render(self):
		user = frappe.get_doc("User", self.user)
		user.bio = "Hosts poetry nights."
		with patch("frappe.in_test", False), patch("frappe.enqueue") as enqueue:
			user.save(ignore_permissions=True)

		self.assertEqual(self.queued_profiles(enqueue), {self.team})

	def test_saving_the_owner_unchanged_queues_nothing(self):
		with patch("frappe.in_test", False), patch("frappe.enqueue") as enqueue:
			frappe.get_doc("User", self.user).save(ignore_permissions=True)

		self.assertEqual(self.queued_profiles(enqueue), set())

	def test_saving_an_event_queues_the_profile_render(self):
		event = frappe.get_doc("Buzz Event", self.event)
		with patch("frappe.in_test", False), patch("frappe.enqueue") as enqueue:
			event.save()

		self.assertEqual(self.queued_profiles(enqueue), {self.team})

	def team_doc(self):
		return frappe.get_doc("Buzz Team", self.team)

	def image(self) -> ProfileOgImage:
		team = self.team_doc()
		return ProfileOgImage(team, profile_owner(team))

	def queued_profiles(self, enqueue) -> set:
		return {
			call.kwargs["team_name"]
			for call in enqueue.call_args_list
			if call.args and call.args[0] == "buzz.events.profile_og_image.generate"
		}

	def og_image(self) -> str:
		return frappe.db.get_value("Buzz Team", self.team, "og_image")

	def og_files(self) -> list:
		return frappe.get_all(
			"File",
			filters={"attached_to_name": self.team, "attached_to_field": "og_image"},
			pluck="file_url",
		)
