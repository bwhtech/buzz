# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

from frappe.website.utils import cleanup_page_name
from frappe.website.website_generator import WebsiteGenerator

from buzz.www.site_header import apply_site_context

# Paths the app serves itself; a topic named after one moves aside instead of hiding the page.
RESERVED_ROUTES = {"community"}


class EventTopic(WebsiteGenerator):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		icon_svg: DF.Code | None
		is_published: DF.Check
		is_standard: DF.Check
		route: DF.Data | None
		short_description: DF.SmallText | None
	# end: auto-generated types

	def validate(self):
		# A disabled topic cannot be picked on events, so its page would stay empty.
		if not self.enabled:
			self.is_published = 0
		super().validate()

	def make_route(self) -> str:
		route = cleanup_page_name(self.name)
		return f"{route}-events" if route in RESERVED_ROUTES else route

	def get_context(self, context):
		from buzz.events.doctype.event_topic.topic_page import TopicPage

		apply_site_context(context)
		context.no_cache = 1
		context.update(TopicPage(self).as_context())
