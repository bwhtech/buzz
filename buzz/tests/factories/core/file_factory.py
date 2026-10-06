from typing import Any

import frappe
from frappe.core.doctype.file.file import File
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory


class FileFactory(BaseFactory[File]):
	"""A small public text file. Pass `content` and `file_name` for an image."""

	doctype = "File"

	@property
	def default_attributes(self) -> dict[str, Any]:
		return {
			"file_name": f"{frappe.generate_hash(length=8)}.txt",
			"content": b"factory file",
			"is_private": 0,
		}
