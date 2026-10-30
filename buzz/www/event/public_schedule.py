from functools import cached_property

import frappe
from frappe import _
from frappe.utils import comma_sep, get_time

from buzz.api.schedule.services import speaker_profiles
from buzz.events.doctype.buzz_schedule_item_type.buzz_schedule_item_type import HEX_COLOR, THEME_COLORS
from buzz.www.event.date_range import format_day, format_time, format_time_range, join_parts
from buzz.www.event.schedule_grid import ScheduleGrid

MUTED_COLOR = "var(--ink-muted)"


def join_names(names: list[str]) -> str:
	return comma_sep(names, _("{0} and {1}"), add_quotes=False)


def minutes_of(time) -> int:
	return int(get_time(time).hour * 60 + get_time(time).minute)


def is_talk(item) -> bool:
	return item.reference_doctype == "Event Talk"


def speaker_summary(profile) -> dict:
	return {
		"name": profile.display_name,
		"role": join_parts([profile.designation, profile.company], ", "),
		"image": profile.display_image,
	}


def css_color(color: str | None) -> str:
	if color in THEME_COLORS:
		return f"var(--schedule-{color})"
	return color if color and HEX_COLOR.match(color) else MUTED_COLOR


def duration_label(seconds) -> str:
	minutes = int((seconds or 0) // 60)
	hours, minutes = divmod(minutes, 60)
	parts = [_("{0} hr").format(hours) if hours else "", _("{0} min").format(minutes) if minutes else ""]
	return join_parts(parts, " ")


def count_label(count: int) -> str:
	return _("1 session") if count == 1 else _("{0} sessions").format(count)


def group_into_slots(rows: list[dict]) -> list[dict]:
	"""Rows starting together share a slot, except all-room rows, which stand alone."""
	slots = []
	for row in rows:
		last = slots[-1] if slots else None
		if last and last["start"] == row["start"] and not (last["all_rooms"] or row["all_rooms"]):
			last["rows"].append(row)
		else:
			slots.append({"start": row["start"], "all_rooms": row["all_rooms"], "rows": [row]})
	return slots


class PublicSchedule:
	"""The event's published schedule, shaped for the public event page."""

	def __init__(self, event: str):
		self.name = frappe.db.get_value("Buzz Schedule", {"event": event, "is_published": 1})

	@cached_property
	def days(self) -> list[dict]:
		if not self.name:
			return []
		days = [self.day(day) for day in self.document.day_list()]
		return [day for day in days if day["rows"]]

	@cached_property
	def rooms(self) -> list[dict]:
		"""Empty with a single room: a label or filter would only repeat itself."""
		return self.tracks if len(self.tracks) > 1 else []

	@cached_property
	def document(self):
		return frappe.get_doc("Buzz Schedule", self.name)

	@cached_property
	def tracks(self) -> list[dict]:
		if not self.name:
			return []
		used = {item.track for item in self.document.items if item.track}
		return frappe.get_all(
			"Buzz Schedule Track",
			or_filters={"schedule": self.name, "name": ["in", list(used) or [""]]},
			fields=["name", "title"],
			order_by="sequence asc, creation asc",
		)

	@cached_property
	def items(self) -> list:
		return sorted(
			self.document.items,
			key=lambda item: (get_time(item.start_time), self.room_positions.get(item.track, -1)),
		)

	@cached_property
	def room_positions(self) -> dict:
		return {track.name: position for position, track in enumerate(self.tracks)}

	@cached_property
	def room_titles(self) -> dict:
		return {room.name: room.title for room in self.rooms}

	def day(self, day: dict) -> dict:
		rows = [self.row(item) for item in self.items if str(item.date) == day["date"]]
		sessions = len([row for row in rows if not row["all_rooms"]])
		label = day["label"] or format_day(day["date"])
		return {
			"day": label,
			"key": day["date"],
			"caption": join_parts(
				[format_day(day["date"]) if day["label"] else "", count_label(sessions)], " · "
			),
			"rows": rows,
			"slots": group_into_slots(rows),
			"grid": ScheduleGrid(rows, self.tracks).as_dict(),
		}

	def row(self, item) -> dict:
		people = self.speakers.get(item.reference_document, []) if is_talk(item) else []
		item_type = self.types.get(item.type)
		return {
			"start": format_time(item.start_time),
			"start_minutes": minutes_of(item.start_time),
			"duration_minutes": int((item.duration or 0) // 60),
			"time": format_time_range(item.start_time, item.end_time),
			"title": item.title,
			"type": item_type.title if item_type else "",
			"color": css_color(item_type.color if item_type else None),
			"duration": duration_label(item.duration),
			"all_rooms": bool(item.all_tracks),
			"room": self.room_title(item),
			"room_key": "" if item.all_tracks else item.track or "",
			"people": people,
			"speakers": join_names([person["name"] for person in people]),
			"abstract": self.abstracts.get(item.reference_document, "") if is_talk(item) else "",
		}

	def room_title(self, item) -> str:
		return "" if item.all_tracks else self.room_titles.get(item.track, "")

	@cached_property
	def types(self) -> dict:
		names = list({item.type for item in self.document.items})
		rows = frappe.get_all(
			"Buzz Schedule Item Type", filters={"name": ["in", names]}, fields=["name", "title", "color"]
		)
		return {row.name: row for row in rows}

	@cached_property
	def abstracts(self) -> dict:
		rows = frappe.get_all(
			"Event Talk", filters={"name": ["in", self.talk_names]}, fields=["name", "description"]
		)
		return {str(row.name): row.description or "" for row in rows}

	@cached_property
	def talk_names(self) -> list[str]:
		return [item.reference_document for item in self.document.items if is_talk(item)]

	@cached_property
	def speakers(self) -> dict:
		profiles = speaker_profiles(self.talk_names, ["designation", "company", "display_image"])
		return {talk: [speaker_summary(profile) for profile in people] for talk, people in profiles.items()}
