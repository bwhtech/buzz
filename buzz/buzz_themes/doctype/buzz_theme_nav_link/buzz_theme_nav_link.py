import frappe
from frappe.model.document import Document
from frappe.utils import validate_url

ALLOWED_URL_SCHEMES = ["http", "https"]


class BuzzThemeNavLink(Document):
	def validate(self):
		self.validate_link_url()

	def validate_link_url(self):
		"""Header links are rendered straight into href, so a `javascript:` URL here would be
		stored XSS on every themed page. frappe's own validate_url accepts any scheme unless
		told otherwise, and rejects site-relative paths outright, so both cases are checked here."""
		url = (self.url or "").strip()

		if url.startswith("/"):
			return

		if not validate_url(url, valid_schemes=ALLOWED_URL_SCHEMES):
			frappe.throw(
				frappe._(
					"{0} is not a valid link. Use a site path like /events or a full http(s) URL."
				).format(frappe.bold(url)),
				title=frappe._("Invalid Header Link"),
			)
