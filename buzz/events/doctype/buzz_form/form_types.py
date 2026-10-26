import re

import frappe
from frappe import _, scrub
from frappe.utils import get_datetime, get_datetime_in_timezone, get_system_timezone

from buzz.api.forms.fields import parse_excluded_fields
from buzz.utils import build_event_datetimes

SPONSORSHIP_FORM_DOCTYPE = "Sponsorship Enquiry"
TALK_PROPOSAL_FORM_DOCTYPE = "Talk Proposal"
EVENT_FEEDBACK_FORM_DOCTYPE = "Event Feedback"
REGISTRATION_FORM_DOCTYPE = "Event Booking"
REGISTRATION_ROUTE = "register"
# What the booking page and the registration report call each kind of registration question.
APPLIED_TO_BY_ASKED_PER = {"Booking": "Booking", "Attendee": "Ticket"}
# What a template carries of each question; the form it belongs to travels beside it.
QUESTION_FIELD_NAMES = (
	"enabled",
	"label",
	"fieldname",
	"fieldtype",
	"options",
	"mandatory",
	"placeholder",
	"default_value",
	"description",
	"depends_on",
	"mandatory_depends_on",
	"asked_per",
)

ENQUIRY_FIELDS = frozenset(
	{"company_name", "company_logo", "website", "tier", "country", "phone", "contact_email"}
)


def event_now(time_zone: str | None):
	"""The current wall clock of the event's time zone, which is how cutoffs are written."""
	return get_datetime_in_timezone(time_zone or get_system_timezone()).replace(tzinfo=None)


def is_form_closed(publish, auto_close_at, time_zone: str | None) -> bool:
	if not publish:
		return True
	return bool(auto_close_at) and get_datetime(auto_close_at) < event_now(time_zone)


def is_registration_closed(form, event) -> bool:
	"""No form takes no registrations; without a cutoff, they close once the event has ended."""
	if not form or is_form_closed(form.publish, form.auto_close_at, event.time_zone):
		return True
	return not form.auto_close_at and event_now(event.time_zone) > build_event_datetimes(event)[1]


def event_time_zone(event: str) -> str | None:
	return frappe.get_cached_value("Buzz Event", event, "time_zone")


def event_form(event: str, form_doctype: str):
	"""The event's form of that doctype; every event gets the default ones, a template may name another."""
	name = frappe.db.get_value("Buzz Form", {"event": event, "form_doctype": form_doctype})
	return frappe.get_doc("Buzz Form", name) if name else None


class FormType:
	one_per_event = False
	has_page = True
	reserved_fieldnames = frozenset()

	def question_key(self, question):
		return question.fieldname

	def condition_fields(self, form, question) -> dict:
		"""Fields a condition on this question may name besides the form's own fields."""
		return {}

	def is_closed(self, form) -> bool:
		return is_form_closed(form.publish, form.auto_close_at, event_time_zone(form.event))

	def close(self, form):
		form.publish = 0

	def open(self, form):
		form.publish = 1
		form.auto_close_at = None

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


def close_at_now(form):
	"""Close by cutoff, keeping the page up to show its closed message."""
	form.publish = 1
	form.auto_close_at = event_now(event_time_zone(form.event))


class TalkProposalFormType(FormType):
	one_per_event = True
	close = staticmethod(close_at_now)


class RegistrationFormType(FormType):
	one_per_event = True
	has_page = False  # registration is served by /book-tickets, not /b/<event>/<route>

	def question_key(self, question):
		# A booking and an attendee question may share a fieldname.
		return (question.asked_per, question.fieldname)

	def is_closed(self, form) -> bool:
		event = frappe.get_cached_doc("Buzz Event", form.event)
		return is_registration_closed(form, event)

	close = staticmethod(close_at_now)

	def condition_fields(self, form, question) -> dict:
		if question.asked_per != "Attendee":
			return {}
		return {"ticket_type": frappe.get_meta("Event Booking Attendee").get_field("ticket_type")}


FORM_TYPES = {
	SPONSORSHIP_FORM_DOCTYPE: SponsorshipFormType(),
	TALK_PROPOSAL_FORM_DOCTYPE: TalkProposalFormType(),
	REGISTRATION_FORM_DOCTYPE: RegistrationFormType(),
}

# Created with every event, closed: an organiser opens one when they mean to.
DEFAULT_FORMS = (
	(SPONSORSHIP_FORM_DOCTYPE, "enquire-sponsorship", "Sponsorship enquiry"),
	(EVENT_FEEDBACK_FORM_DOCTYPE, "feedback", "Feedback"),
	(TALK_PROPOSAL_FORM_DOCTYPE, "propose-talk", "Talk proposal"),
	(REGISTRATION_FORM_DOCTYPE, REGISTRATION_ROUTE, "Registration"),
)


def form_type(form_doctype: str) -> FormType:
	return FORM_TYPES.get(form_doctype, FormType())


def create_default_forms(event: str):
	for form_doctype, route, title in DEFAULT_FORMS:
		form = frappe.get_doc(
			{
				"doctype": "Buzz Form",
				"title": title,
				"event": event,
				"form_doctype": form_doctype,
				"route": route,
				"publish": 0,
			}
		)
		if form_doctype == REGISTRATION_FORM_DOCTYPE:
			# Organisers open registrations once tickets and details are ready.
			form_type(form_doctype).close(form)
		form.insert(ignore_permissions=True)


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
