import re
from typing import ClassVar

import frappe
from frappe import _, scrub
from frappe.utils import get_datetime, get_datetime_in_timezone, get_system_timezone

from buzz.api.forms.fields import get_renderable_fields, system_exclude_fields
from buzz.utils import build_event_datetimes

SPONSORSHIP_FORM_DOCTYPE = "Sponsorship Enquiry"
TALK_PROPOSAL_FORM_DOCTYPE = "Talk Proposal"
EVENT_FEEDBACK_FORM_DOCTYPE = "Event Feedback"
REGISTRATION_FORM_DOCTYPE = "Event Booking"
REGISTRATION_ROUTE = "register"
ATTENDEE_FORM_DOCTYPE = "Event Booking Attendee"
ATTENDEE_ROUTE = "register-attendee"
# What the booking page and the registration report call each registration form's questions.
APPLIED_TO_BY_FORM_DOCTYPE = {REGISTRATION_FORM_DOCTYPE: "Booking", ATTENDEE_FORM_DOCTYPE: "Ticket"}
# What a template carries of each question; the form it belongs to travels beside it.
QUESTION_FIELD_NAMES = (
	"enabled",
	"label",
	"fieldname",
	"fieldtype",
	"options",
	"mandatory",
	"width",
	"placeholder",
	"default_value",
	"description",
)
# A template keeps each question's own show and required conditions; a form keeps them as rules.
TEMPLATE_CONDITION_ACTIONS = {"depends_on": "show", "mandatory_depends_on": "require"}

ENQUIRY_FIELDS = frozenset(
	{"company_name", "company_logo", "website", "tier", "country", "phone", "contact_email"}
)


def now_in_event_time_zone(time_zone: str | None):
	"""The current wall clock of the event's time zone, which is how cutoffs are written."""
	return get_datetime_in_timezone(time_zone or get_system_timezone()).replace(tzinfo=None)


def is_form_closed(publish, auto_close_at, time_zone: str | None) -> bool:
	if not publish:
		return True
	return bool(auto_close_at) and get_datetime(auto_close_at) < now_in_event_time_zone(time_zone)


def is_registration_closed(form, event) -> bool:
	"""No form takes no registrations; without a cutoff, they close once the event has ended."""
	if not form or is_form_closed(form.publish, form.auto_close_at, event.time_zone):
		return True
	return (
		not form.auto_close_at and now_in_event_time_zone(event.time_zone) > build_event_datetimes(event)[1]
	)


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
	# Standard fields the organiser may move or rename but never hide.
	locked_fieldnames = frozenset()
	# The only standard fields offered, in order, with the label the booking page shows.
	# None offers every renderable field under its doctype label.
	core_fields: ClassVar[dict[str, str] | None] = None
	core_width = "Full"
	answers_field = "additional_fields"

	def standard_fields(self, form_doctype: str) -> dict:
		"""The doctype's own fields the form offers."""
		fields = get_renderable_fields(form_doctype, system_exclude_fields(form_doctype))
		if self.core_fields is not None:
			return {fieldname: fields[fieldname] for fieldname in self.core_fields}
		return fields if self.has_page else {}

	def default_label(self, fieldname: str, df) -> str:
		return (self.core_fields or {}).get(fieldname) or df.label

	def is_closed(self, form) -> bool:
		return is_form_closed(form.publish, form.auto_close_at, event_time_zone(form.event))

	def close(self, form):
		form.publish = 0

	def open(self, form):
		form.publish = 1
		form.auto_close_at = None

	def validate(self, form):
		if self.one_per_event and self.other_forms_of_event(form):
			frappe.throw(_("This event already has a {0} form.").format(_(form.form_doctype)))

	def other_forms_of_event(self, form) -> list[str]:
		filters = {"event": form.event, "form_doctype": form.form_doctype}
		if form.name:
			filters["name"] = ["!=", form.name]
		return frappe.get_all("Buzz Form", filters=filters, pluck="name", limit=1)


class SponsorshipFormType(FormType):
	one_per_event = True
	reserved_fieldnames = ENQUIRY_FIELDS
	locked_fieldnames = frozenset({"contact_email"})

	def standard_fields(self, form_doctype: str) -> dict:
		"""An enquiry also holds the team's own notes; applicants see only these."""
		fields = super().standard_fields(form_doctype)
		return {fieldname: df for fieldname, df in fields.items() if fieldname in ENQUIRY_FIELDS}

	def validate(self, form):
		super().validate(form)
		form.login_required = 0


def close_with_cutoff(form):
	"""Close by cutoff, keeping the page up to show its closed message."""
	form.publish = 1
	form.auto_close_at = now_in_event_time_zone(event_time_zone(form.event))


class TalkProposalFormType(FormType):
	one_per_event = True
	close = staticmethod(close_with_cutoff)


class RegistrationFormType(FormType):
	one_per_event = True
	has_page = False  # registration is served by /book-tickets, not /b/<event>/<route>
	core_fields: ClassVar[dict[str, str]] = {
		"buyer_name": "Full name",
		"buyer_email": "Email",
		"buyer_phone": "Phone",
	}
	locked_fieldnames = frozenset({"buyer_name", "buyer_email"})

	def is_closed(self, form) -> bool:
		event = frappe.get_cached_doc("Buzz Event", form.event)
		return is_registration_closed(form, event)

	close = staticmethod(close_with_cutoff)


class AttendeeFormType(FormType):
	"""Questions asked once per attendee; the registration form owns every setting."""

	one_per_event = True
	has_page = False
	core_fields: ClassVar[dict[str, str]] = {
		"first_name": "First name",
		"last_name": "Last name",
		"email": "Email",
	}
	locked_fieldnames = frozenset({"first_name", "email"})
	answers_field = "custom_fields"

	def is_closed(self, form) -> bool:
		event = frappe.get_cached_doc("Buzz Event", form.event)
		return is_registration_closed(event_form(form.event, REGISTRATION_FORM_DOCTYPE), event)

	def close(self, form):
		pass

	def open(self, form):
		pass


FORM_TYPES = {
	SPONSORSHIP_FORM_DOCTYPE: SponsorshipFormType(),
	TALK_PROPOSAL_FORM_DOCTYPE: TalkProposalFormType(),
	REGISTRATION_FORM_DOCTYPE: RegistrationFormType(),
	ATTENDEE_FORM_DOCTYPE: AttendeeFormType(),
}

# Created with every event, closed: an organiser opens one when they mean to.
DEFAULT_FORMS = (
	(SPONSORSHIP_FORM_DOCTYPE, "enquire-sponsorship", "Sponsorship enquiry"),
	(EVENT_FEEDBACK_FORM_DOCTYPE, "feedback", "Feedback"),
	(TALK_PROPOSAL_FORM_DOCTYPE, "propose-talk", "Talk proposal"),
	(REGISTRATION_FORM_DOCTYPE, REGISTRATION_ROUTE, "Registration"),
	(ATTENDEE_FORM_DOCTYPE, ATTENDEE_ROUTE, "Attendee details"),
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


def template_rules(field) -> list[dict]:
	"""A template question's own conditions, as rules on the form it joins."""
	return [
		{
			"match": "all",
			"conditions": frappe.parse_json(field.get(key)),
			"actions": [[action, field.fieldname]],
		}
		for key, action in TEMPLATE_CONDITION_ACTIONS.items()
		if field.get(key)
	]


def template_conditions(rules: list[dict], fieldname: str) -> dict:
	"""The reverse: a rule a template can carry acts on this one question alone, matching all."""
	conditions = {}
	for key, action in TEMPLATE_CONDITION_ACTIONS.items():
		rule = next(
			(
				rule
				for rule in rules
				if rule.get("match", "all") == "all" and rule.get("actions") == [[action, fieldname]]
			),
			None,
		)
		conditions[key] = frappe.as_json(rule["conditions"], indent=None) if rule else None
	return conditions


def unique_fieldname(label_or_fieldname: str, taken: set, reserved: frozenset) -> str:
	"""Legacy questions were never held to the new key rules, so reshape rather than refuse.

	A site whose form asks for a "Website" is ordinary, and failing the whole migrate over it
	strands every other event. Old answers keep their own fieldname copy, so a rename here
	only affects what arrives next.
	"""
	name = re.sub(r"[^a-z0-9_]", "_", scrub(label_or_fieldname or "")).strip("_")
	if not name[:1].isalpha():
		name = f"question_{name}"
	candidate, suffix = name, 2
	while candidate in taken or candidate in reserved:
		candidate, suffix = f"{name}_{suffix}", suffix + 1
	taken.add(candidate)
	return candidate
