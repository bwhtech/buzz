from frappe.website.doctype.website_settings.website_settings import modify_header_footer_items

from buzz.www.site_header import SiteHeader


def buzz_footer() -> dict:
	"""Context for the Buzz Footer web template, which any website page may render."""
	return SiteFooter().as_context()


class SiteFooter:
	def __init__(self):
		self.header = SiteHeader()
		self.settings = self.header.settings

	def as_context(self) -> dict:
		links = self.links()
		return {
			"brand": self.header.brand(),
			"logo": self.settings.footer_logo,
			"address": self.settings.address,
			"copyright": self.settings.copyright,
			"powered_by": self.settings.footer_powered,
			"groups": [link for link in links if link["child_items"]],
			"links": [link for link in links if link["url"] and not link["child_items"]],
		}

	def links(self) -> list[dict]:
		items = modify_header_footer_items(self.settings.footer_items)
		return [self.header.link(item) for item in items if not item.parent_label]
