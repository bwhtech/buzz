from typing import Any

import frappe
from faker import Faker
from frappe.core.doctype.user.user import User
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

_fake = Faker()


class UserFactory(BaseFactory[User]):
	doctype = "User"

	@classmethod
	def create_once(cls, email: str) -> User:
		"""Reuse an existing user: test users leak, and User creation is throttled at 60 an hour."""
		if frappe.db.exists("User", email):
			return frappe.get_doc("User", email)
		# A fixed identity is a fixture, so it must not depend on who the session user is.
		return cls.create(email=email, flags={"ignore_permissions": True})

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {
			"email": _fake.unique.email(),
			"first_name": _fake.first_name(),
			"last_name": _fake.last_name(),
			"send_welcome_email": 0,
		}
