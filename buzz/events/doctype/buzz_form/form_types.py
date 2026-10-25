import re

import frappe
from frappe import _, scrub

from buzz.api.forms.fields import parse_excluded_fields

SPONSORSHIP_FORM_DOCTYPE = "Sponsorship Enquiry"
TALK_PROPOSAL_FORM_DOCTYPE = "Talk Proposal"
EVENT_FEEDBACK_FORM_DOCTYPE = "Event Feedback"

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


class TalkProposalFormType(FormType):
	one_per_event = True


FORM_TYPES = {
	SPONSORSHIP_FORM_DOCTYPE: SponsorshipFormType(),
	TALK_PROPOSAL_FORM_DOCTYPE: TalkProposalFormType(),
}

# Created with every event, unpublished: an organiser opens one when they mean to.
DEFAULT_FORMS = (
	(SPONSORSHIP_FORM_DOCTYPE, "enquire-sponsorship", "Sponsorship enquiry"),
	(EVENT_FEEDBACK_FORM_DOCTYPE, "feedback", "Feedback"),
	(TALK_PROPOSAL_FORM_DOCTYPE, "propose-talk", "Talk proposal"),
)


def form_type(form_doctype: str) -> FormType:
	return FORM_TYPES.get(form_doctype, FormType())


def create_default_forms(event: str):
	for form_doctype, route, title in DEFAULT_FORMS:
		frappe.get_doc(
			{
				"doctype": "Buzz Form",
				"title": title,
				"event": event,
				"form_doctype": form_doctype,
				"route": route,
			}
		).insert(ignore_permissions=True)


def usable_fieldname(label_or_fieldname: str, taken: set, reserved: frozenset) -> str:
	"""Legacy questions were never held to the new key rules, so reshape rather than refuse.

	A site whose form asks for a "Website" is ordinary, and failing the whole migrate over it
	strands every other event. Old answers keep their own fieldname copy, so a rename here
	only affects what arrives next.
	"""
	name = re.sub(r"[^a-z0-9_]", "_", scrub(label_or_fieldname or ""))
	if not name[:1].isalpha():
		name = f"question_{name}"
	candidate, suffix = name, 2
	while candidate in taken or candidate in reserved:
		candidate, suffix = f"{name}_{suffix}", suffix + 1
	taken.add(candidate)
	return candidate
