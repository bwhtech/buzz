import re
from typing import ClassVar

import frappe
from frappe import _
from frappe.utils import get_time, getdate, validate_email_address

from buzz.api.imports.schemas import ImportOption
from buzz.api.imports.services import Field, Importer

SEPARATOR = re.compile(r"\s*[,;]\s*")
SLOT_FIELDS = {"date", "start_time", "end_time"}


def split(value: str | None) -> list[str]:
	return [part for part in SEPARATOR.split(value or "") if part]


class TalkImporter(Importer):
	"""One row is an accepted talk with its speakers, and a schedule slot when it names one."""

	section = "talks"
	noun = "talks"
	fields: ClassVar[dict[str, Field]] = {
		"title": Field("Title", True, ("talk_title", "talk", "talk_name", "session", "session_title")),
		"description": Field("Description", aliases=("abstract", "summary", "details")),
		"speaker_email": Field("Speaker Email", True, ("email", "speaker_emails", "emails")),
		"speaker_name": Field("Speaker Name", aliases=("speaker", "speakers", "speaker_names", "name")),
		"designation": Field("Designation", aliases=("job_title", "role", "position")),
		"company": Field("Company", aliases=("organisation", "organization", "company_name", "org")),
		"track": Field("Track", aliases=("room", "hall", "stage")),
		"date": Field("Date", aliases=("day",)),
		"start_time": Field("Start Time", aliases=("start", "starts", "slot", "from", "time")),
		"end_time": Field("End Time", aliases=("end", "ends", "to", "until")),
	}
	value_fields: ClassVar[dict[str, bool]] = {"track": True}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.slots: list[dict] = []

	def options(self, field: str) -> list[ImportOption]:
		tracks = frappe.get_all("Event Track", filters={"event": self.event}, pluck="name")
		return [ImportOption(value=track, label=track) for track in tracks]

	def value_issues(self) -> list:
		# A track only places a talk on the schedule, which needs its date and times as well.
		return super().value_issues() if SLOT_FIELDS <= set(self.mapping) else []

	def create_value(self, field: str, raw: str) -> str:
		# Track names are unique across events, so a name another event holds gets this one's id.
		name = f"{raw} ({self.event})" if frappe.db.exists("Event Track", raw) else raw
		return frappe.get_doc({"doctype": "Event Track", "event": self.event}).insert(set_name=name).name

	def row_error(self, record: dict) -> str | None:
		if error := super().row_error(record):
			return error
		for email in split(record["speaker_email"]):
			if not validate_email_address(email):
				return _("{0} isn't an email.").format(email)
		return self.slot_error(record)

	def slot_error(self, record: dict) -> str | None:
		try:
			for field in ("start_time", "end_time"):
				record[field] = get_time(record[field]) if record.get(field) else None
			record["date"] = getdate(record["date"]) if record.get("date") else None
		except Exception:
			return _("The date or time of this talk isn't readable.")
		if record["start_time"] and record["end_time"] and record["end_time"] <= record["start_time"]:
			return _("The talk ends before it starts.")
		return None

	def duplicate_keys(self, record: dict) -> list[str]:
		return [record["title"].lower()]

	def existing_keys(self) -> set[str]:
		filters = {"event": self.event}
		titles = frappe.get_all("Talk Proposal", filters=filters, pluck="title")
		titles += frappe.get_all("Event Talk", filters=filters, pluck="title")
		return {title.lower() for title in titles}

	def notes(self) -> list[str]:
		emails = {
			email.lower() for record in self.sorted_records[0] for email in split(record["speaker_email"])
		}
		known = frappe.get_all("User", filters={"name": ["in", list(emails)]}, pluck="name") if emails else []
		new = len(emails) - len(known)
		notes = super().notes()
		if new:
			notes.append(_("Speakers new to Buzz, who get a profile: {0}.").format(new))
		return notes

	def import_record(self, record: dict) -> None:
		proposal = frappe.get_doc(
			{
				"doctype": "Talk Proposal",
				"event": self.event,
				"title": record["title"],
				"description": record.get("description"),
				"speakers": self.speakers(record),
			}
		).insert()
		self.create_users(proposal)
		talk = proposal.create_talk()
		self.fill_profiles(talk, record)
		self.schedule(talk, record)

	def speakers(self, record: dict) -> list[dict]:
		names = split(record.get("speaker_name"))
		speakers = []
		for index, email in enumerate(split(record["speaker_email"])):
			name = names[index] if index < len(names) else email.split("@")[0]
			first, _space, last = name.partition(" ")
			speakers.append({"first_name": first, "last_name": last, "email": email})
		return speakers

	def create_users(self, proposal) -> None:
		"""Ahead of create_talk, which would make them with a welcome email the user may not want."""
		for speaker in proposal.speakers:
			if not frappe.db.exists("User", speaker.email):
				frappe.get_doc(
					{
						"doctype": "User",
						"first_name": speaker.first_name,
						"last_name": speaker.last_name,
						"email": speaker.email,
						"user_type": "Website User",
						"send_welcome_email": int(self.send_emails),
					}
				).insert(ignore_permissions=True)

	def fill_profiles(self, talk, record: dict) -> None:
		details = {field: record.get(field) for field in ("designation", "company") if record.get(field)}
		for row in talk.speakers if details else []:
			profile = frappe.get_doc("Speaker Profile", row.speaker)
			profile.update({field: value for field, value in details.items() if not profile.get(field)})
			profile.save()

	def schedule(self, talk, record: dict) -> None:
		if record.get("track") and record["date"] and record["start_time"] and record["end_time"]:
			# validate_schedule compares the date with the event's and diffs the times as text.
			times = {field: str(record[field]) for field in ("start_time", "end_time")}
			self.slots.append(
				{
					**times,
					"date": record["date"],
					"talk": talk.name,
					"track": record["track"],
					"row": record["row"],
				}
			)

	def finish(self) -> None:
		"""Tracks are made here, outside the rows' savepoints, so a failed row cannot roll one back."""
		if not self.slots:
			return
		event = frappe.get_doc("Buzz Event", self.event)
		for slot in self.slots:
			row = event.append(
				"schedule", {**slot, "type": "Talk", "track": self.resolve("track", slot["track"])}
			)
			try:
				event.validate_schedule()
			except frappe.ValidationError:
				event.schedule.remove(row)
				self.run_notes.append(
					_("Row {0} is imported, but its slot is outside the event's dates or hours.").format(
						slot["row"]
					)
				)
		frappe.clear_messages()
		event.save()
