from typing import Any

import frappe
from faker import Faker
from frappe.email.doctype.email_template.email_template import EmailTemplate
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

_fake = Faker()


class EmailTemplateFactory(BaseFactory[EmailTemplate]):
	doctype = "Email Template"

	@property
	def default_attributes(self) -> dict[str, Any]:
		# Prompt-autonamed, and rows outlive a run, so a hash beats Faker's per-process `unique`.
		return {
			"name": f"Template {frappe.generate_hash(length=8)}",
			"subject": _fake.sentence(),
			"response": f"<p>{_fake.paragraph()}</p>",
		}
