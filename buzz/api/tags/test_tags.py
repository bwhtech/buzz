import frappe

from buzz.api.tags import create_tag, desk, set_tags
from buzz.api.tags.exceptions import EmptyTagLabel, NotTaggable
from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import (
	BuzzTagFactory,
	BuzzTeamMembershipFactory,
	EventSponsorFactory,
	UserFactory,
)


class TestCreateTag(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.viewer = UserFactory.create_once("tags-viewer@example.com").name
		BuzzTeamMembershipFactory.create(team=cls.team_a, user=cls.viewer, team_role="Viewer")

	def create_as(self, user: str, team: str, label: str, document_type: str = "Event Sponsor"):
		with self.set_user(user):
			return create_tag(team, document_type, label)

	def test_same_label_in_two_teams_stays_apart(self):
		tag_a = self.create_as(self.alice, self.team_a, "VIP")
		tag_b = self.create_as(self.bob, self.team_b, "VIP")

		self.assertNotEqual(tag_a.name, tag_b.name)

	def test_same_label_on_two_record_types_stays_apart(self):
		sponsor_tag = self.create_as(self.alice, self.team_a, "Returning")
		event_tag = self.create_as(self.alice, self.team_a, "Returning", "Buzz Event")

		self.assertNotEqual(sponsor_tag.name, event_tag.name)

	def test_color_is_kept_and_defaults_to_gray(self):
		with self.set_user(self.alice):
			colored = create_tag(self.team_a, "Event Sponsor", "Paid", "green")
			plain = create_tag(self.team_a, "Event Sponsor", "Booth")

		self.assertEqual((colored.color, plain.color), ("green", "gray"))

	def test_existing_label_returns_that_tag(self):
		first = self.create_as(self.alice, self.team_a, "Follow up")
		again = self.create_as(self.alice, self.team_a, "  follow   UP ")

		self.assertEqual(again.name, first.name)

	def test_database_refuses_a_second_tag_with_the_same_label(self):
		BuzzTagFactory.create(team=self.team_a, label="Speaker")

		with self.assertRaises(frappe.UniqueValidationError):
			BuzzTagFactory.create(team=self.team_a, label="speaker")

	def test_viewer_and_outsider_cannot_create(self):
		for user in (self.viewer, self.outsider):
			with self.assertRaises(frappe.PermissionError):
				self.create_as(user, self.team_a, "Nope")

	def test_blank_label_and_untaggable_type_are_refused(self):
		with self.assertRaises(EmptyTagLabel):
			self.create_as(self.alice, self.team_a, "   ")
		with self.assertRaises(NotTaggable):
			self.create_as(self.alice, self.team_a, "Paid", "Event Booking")

	def test_every_member_reads_their_team_tags_only(self):
		own = BuzzTagFactory.create(team=self.team_a).name
		other = BuzzTagFactory.create(team=self.team_b).name

		visible = self.list_as(self.viewer, "Buzz Tag")

		self.assertIn(own, visible)
		self.assertNotIn(other, visible)


class TestSetTags(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.viewer = UserFactory.create_once("tags-viewer@example.com").name
		BuzzTeamMembershipFactory.create(team=cls.team_a, user=cls.viewer, team_role="Viewer")

	def setUp(self):
		super().setUp()
		self.sponsor = EventSponsorFactory.create(event=self.event_a).name
		self.vip = BuzzTagFactory.create(team=self.team_a).name
		self.gold = BuzzTagFactory.create(team=self.team_a).name

	def tag_sponsor(self, *tags: str, user: str | None = None) -> set[str]:
		with self.set_user(user or self.alice):
			return {tag.name for tag in set_tags("Event Sponsor", self.sponsor, list(tags))}

	def test_replaces_the_record_tags(self):
		self.assertEqual(self.tag_sponsor(self.vip, self.gold), {self.vip, self.gold})
		self.assertEqual(self.tag_sponsor(self.gold), {self.gold})
		self.assertEqual(self.tag_sponsor(), set())

	def test_tag_of_another_team_or_type_is_refused(self):
		other_team = BuzzTagFactory.create(team=self.team_b).name
		event_tag = BuzzTagFactory.create(team=self.team_a, document_type="Buzz Event").name

		for tag in (other_team, event_tag):
			with self.assertRaises(frappe.ValidationError):
				self.tag_sponsor(tag)

	def test_viewer_cannot_tag(self):
		with self.assertRaises(frappe.PermissionError):
			self.tag_sponsor(self.vip, user=self.viewer)

	def test_event_names_are_integers(self):
		tag = BuzzTagFactory.create(team=self.team_a, document_type="Buzz Event").name

		with self.set_user(self.alice):
			tags = set_tags("Buzz Event", str(self.event_a), [tag])

		self.assertEqual([item.name for item in tags], [tag])

	def test_deleting_the_record_or_the_tag_removes_links(self):
		self.tag_sponsor(self.vip, self.gold)

		frappe.delete_doc("Buzz Tag", self.gold)
		self.assertEqual(frappe.db.count("Buzz Tag Link", {"document_name": self.sponsor}), 1)

		frappe.delete_doc("Event Sponsor", self.sponsor)
		self.assertFalse(frappe.db.exists("Buzz Tag Link", {"document_name": self.sponsor}))


class TestDeskTags(TeamPermissionTestCase):
	def setUp(self):
		super().setUp()
		self.sponsor = EventSponsorFactory.create(event=self.event_a).name

	def desk_tags(self) -> str:
		return frappe.db.get_value("Event Sponsor", self.sponsor, "_user_tags")

	def test_buzz_tags_show_in_desk_and_follow_renames_and_deletes(self):
		vip = BuzzTagFactory.create(team=self.team_a, label="VIP")
		gold = BuzzTagFactory.create(team=self.team_a, label="Gold")
		with self.set_user(self.alice):
			set_tags("Event Sponsor", self.sponsor, [vip.name, gold.name])
		self.assertEqual(self.desk_tags(), "Gold,VIP")

		vip.label = "Headline"
		vip.save()
		self.assertEqual(self.desk_tags(), "Gold,Headline")

		gold.delete()
		self.assertEqual(self.desk_tags(), "Headline")

	def test_desk_editor_adds_and_removes_team_tags(self):
		with self.set_user(self.alice):
			desk.add_tag("Returning", "Event Sponsor", self.sponsor)
		tag = frappe.db.get_value(
			"Buzz Tag", {"label": "Returning", "document_type": "Event Sponsor"}, "team"
		)
		self.assertEqual(tag, self.team_a)
		self.assertEqual(self.desk_tags(), "Returning")

		with self.set_user(self.alice):
			desk.remove_tag("Returning", "Event Sponsor", self.sponsor)
		self.assertEqual(self.desk_tags(), "")

	def test_desk_suggests_only_the_users_team_tags(self):
		BuzzTagFactory.create(team=self.team_a, label="Alpha Only")
		BuzzTagFactory.create(team=self.team_b, label="Beta Only")

		with self.set_user(self.alice):
			suggested = desk.get_tags("Event Sponsor", "only")

		self.assertEqual(suggested, ["Alpha Only"])

	def test_label_with_a_comma_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			BuzzTagFactory.create(team=self.team_a, label="Gold, Silver")

	def test_other_doctypes_keep_frappe_tags(self):
		label = f"Frappe {frappe.generate_hash(length=8)}"

		desk.add_tag(label, "User", self.alice)

		self.assertTrue(frappe.db.exists("Tag", label))
		self.assertIn(label, frappe.db.get_value("User", self.alice, "_user_tags"))
		self.assertFalse(frappe.db.exists("Buzz Tag", {"label": label}))
