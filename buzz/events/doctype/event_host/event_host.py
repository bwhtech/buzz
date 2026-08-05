# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class EventHost(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.events.doctype.social_media_link.social_media_link import SocialMediaLink

		about: DF.TextEditor | None
		address: DF.SmallText | None
		by_line: DF.Data | None
		country: DF.Link | None
		logo: DF.AttachImage | None
		social_media_links: DF.Table[SocialMediaLink]
		team: DF.Link
	# end: auto-generated types

	pass
