import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import FileFactory, UserFactory
from buzz.utils import make_file_public

OWNER = "file-publish-owner@example.com"
OTHER_USER = "file-publish-other@example.com"


class TestMakeFilePublic(IntegrationTestCase):
	def setUp(self):
		self.enterContext(self.set_user("Administrator"))
		self.owner = UserFactory.create_once(OWNER).name

	def private_file(self):
		with self.set_user(self.owner):
			return FileFactory.create(is_private=1)

	def is_private(self, file) -> int:
		return frappe.db.get_value("File", file.name, "is_private")

	def test_the_owner_publishes_their_own_file(self):
		file = self.private_file()

		with self.set_user(self.owner):
			url = make_file_public(file.file_url)

		self.assertTrue(url.startswith("/files/"))
		self.assertEqual(self.is_private(file), 0)

	def test_another_user_cannot_publish_it(self):
		file = self.private_file()

		with self.set_user(UserFactory.create_once(OTHER_USER).name):
			self.assertRaises(frappe.PermissionError, make_file_public, file.file_url)

		self.assertEqual(self.is_private(file), 1)

	def test_a_guest_cannot_publish_it(self):
		file = self.private_file()

		with self.set_user("Guest"):
			self.assertRaises(frappe.PermissionError, make_file_public, file.file_url)

		self.assertEqual(self.is_private(file), 1)

	def test_a_guest_publishes_the_file_it_uploaded(self):
		# The public enquiry form uploads as Guest, so that logo must still go public.
		file = FileFactory.create(is_private=1)
		file.db_set("owner", "Guest")
		file.reload()

		with self.set_user("Guest"):
			url = make_file_public(file.file_url)

		self.assertTrue(url.startswith("/files/"))
		self.assertEqual(self.is_private(file), 0)

	def test_a_public_url_is_left_alone(self):
		file = FileFactory.create(is_private=0)

		self.assertEqual(make_file_public(file.file_url), file.file_url)
		self.assertEqual(self.is_private(file), 0)
