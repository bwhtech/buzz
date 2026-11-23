from typing import Any

from frappe.email.doctype.email_queue.email_queue import EmailQueue
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory


class EmailQueueFactory(BaseFactory[EmailQueue]):
	doctype = "Email Queue"

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {
			"sender": "sender@example.com",
			"message": "Subject: Factory email\n\nBody",
			"recipients": [{"recipient": "recipient@example.com"}],
		}
