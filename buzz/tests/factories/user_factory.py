from typing import Any

import frappe
from faker import Faker
from frappe.core.doctype.user.user import User
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

_fake = Faker()


class UserFactory(BaseFactory[User]):
	doctype = "User"

	@classmethod
	def create_once(cls, email: str, **overrides: Any) -> User:
		"""
		Reuse the user at `email` if the site already has one.

		Frappe throttles User creation at `throttle_user_limit` (60) per hour
		(`User.throttle_user_creation`), and test users are not rolled back, so a
		full suite run that mints a fresh user for every fixture trips it. Use this
		wherever the identity is fixed and only one record is ever wanted; use
		`create()` when the test needs a distinct user.
		"""
		if frappe.db.exists("User", email):
			return frappe.get_doc("User", email)
		return cls.create(email=email, **overrides)

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {
			"email": _fake.unique.email(),
			"first_name": _fake.first_name(),
			"last_name": _fake.last_name(),
			"send_welcome_email": 0,
		}
