import frappe
from frappe import _

from buzz.api.forms.fields import parse_excluded_fields

SPONSORSHIP_FORM_DOCTYPE = "Sponsorship Enquiry"

ENQUIRY_FIELDS = frozenset(
	{"company_name", "company_logo", "website", "tier", "country", "phone", "contact_email"}
)


class FormType:
	one_per_event = False
	reserved_fieldnames = frozenset()

	def validate(self, form):
		if self.one_per_event and self.others_for_event(form):
			frappe.throw(_("This event already has a {0} form.").format(_(form.form_doctype)))

	def others_for_event(self, form) -> list[str]:
		filters = {"event": form.event, "form_doctype": form.form_doctype}
		if form.name:
			filters["name"] = ["!=", form.name]
		return frappe.get_all("Buzz Form", filters=filters, pluck="name", limit=1)


class SponsorshipFormType(FormType):
	one_per_event = True
	reserved_fieldnames = ENQUIRY_FIELDS

	def validate(self, form):
		super().validate(form)
		if "contact_email" in (parse_excluded_fields(form.excluded_fields) or set()):
			frappe.throw(_("Contact Email cannot be hidden."))
		form.login_required = 0


FORM_TYPES = {SPONSORSHIP_FORM_DOCTYPE: SponsorshipFormType()}


def form_type(form_doctype: str) -> FormType:
	return FORM_TYPES.get(form_doctype, FormType())


def create_sponsorship_form(event: str):
	return frappe.get_doc(
		{
			"doctype": "Buzz Form",
			"title": "Sponsorship enquiry",
			"event": event,
			"form_doctype": SPONSORSHIP_FORM_DOCTYPE,
			"route": "enquire-sponsorship",
		}
	).insert(ignore_permissions=True)
