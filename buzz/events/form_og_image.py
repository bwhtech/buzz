import frappe
from frappe import _
from frappe.utils import format_date, getdate

from buzz.events.og_image import EventOgImage


class FormOgImage(EventOgImage):
	"""A form's share image: the event's banner and theme, with the form's title and closing date."""

	def __init__(self, form):
		self.form = form
		super().__init__(frappe.get_doc("Buzz Event", form.event), form)

	def build_title(self) -> str:
		return self.form.title

	def build_meta_line(self) -> str:
		closes = self.form.auto_close_at and _("Closes {0}").format(
			format_date(getdate(self.form.auto_close_at), "d MMM")
		)
		return " · ".join(part for part in [self.event.title, closes] if part)
