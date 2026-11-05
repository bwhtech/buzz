import frappe
from frappe.utils import getdate, today

from buzz.api.events.exceptions import CannotManageEvent, EventNotFound
from buzz.api.search.exceptions import UnknownSearchSection
from buzz.api.search.schemas import EventSearchResponse, PaletteEvent, PaletteEventsResponse, SearchGroup
from buzz.api.search.sources import SOURCES
from buzz.permissions import HUMAN_MEMBER_FILTERS, SECTIONS, get_section_access, team_role_access

MINIMUM_TERM_LENGTH = 2


def palette_events(user: str) -> PaletteEventsResponse:
	teams = team_roles(user)
	collaborations = collaborator_access_levels(user)
	if not teams and not collaborations:
		return PaletteEventsResponse(events=[])
	rows = frappe.get_all(
		"Buzz Event",
		or_filters=[["team", "in", list(teams)], ["name", "in", list(collaborations)]],
		fields=["name", "title", "team", "start_date", "end_date"],
		ignore_permissions=True,
	)
	team_titles = dict(
		frappe.get_all(
			"Buzz Team",
			filters={"name": ["in", {row.team for row in rows if row.team}]},
			fields=["name", "team_name"],
			as_list=True,
		)
	)
	events = [palette_event(row, teams, collaborations, team_titles) for row in rows]
	return PaletteEventsResponse(events=sorted_for_palette(events))


def team_roles(user: str) -> dict[str, str]:
	rows = frappe.get_all(
		"Buzz Team Membership",
		filters={**HUMAN_MEMBER_FILTERS, "user": user},
		fields=["team", "team_role"],
		as_list=True,
	)
	return dict(rows)


def collaborator_access_levels(user: str) -> dict[str, dict[str, str | None]]:
	rows = frappe.get_all(
		"Buzz Event Collaborator",
		filters={"user": user, "status": "Accepted"},
		fields=["event", *(f"{section}_access" for section in SECTIONS)],
	)
	levels = {
		str(row.event): {section: row[f"{section}_access"] or None for section in SECTIONS} for row in rows
	}
	return {event: access for event, access in levels.items() if any(access.values())}


def palette_event(row, teams: dict, collaborations: dict, team_titles: dict) -> PaletteEvent:
	if team_role := teams.get(row.team):
		access = team_role_access(team_role)
	else:
		access = collaborations.get(str(row.name), dict.fromkeys(SECTIONS))
	return PaletteEvent(
		name=str(row.name),
		title=row.title,
		team=row.team,
		team_title=team_titles.get(row.team),
		start_date=row.start_date,
		end_date=row.end_date,
		access=access,
	)


def sorted_for_palette(events: list[PaletteEvent]) -> list[PaletteEvent]:
	today_date = getdate(today())
	upcoming, past = [], []
	for event in events:
		(upcoming if (event.end_date or today_date) >= today_date else past).append(event)
	upcoming.sort(key=lambda event: event.start_date or today_date)
	past.sort(key=lambda event: event.start_date or today_date, reverse=True)
	return upcoming + past


class EventSearch:
	"""Searches one event's records across the sections the session user can read."""

	def __init__(self, event: str, section: str | None = None):
		if section and section not in SECTIONS:
			UnknownSearchSection.throw(section=section)
		if not frappe.db.exists("Buzz Event", event):
			EventNotFound.throw()

		self.event = event
		self.access = get_section_access(frappe.session.user, event)
		sources = [source for source in SOURCES if not section or source.section == section]
		self.sources = [source for source in sources if self.can_read(source.section)]
		if not any(self.access.values()):
			CannotManageEvent.throw()

	def can_read(self, section: str) -> bool:
		return bool(self.access.get(section))

	def run(self, term: str) -> EventSearchResponse:
		term = (term or "").strip()
		if len(term) < MINIMUM_TERM_LENGTH:
			return EventSearchResponse(groups=[])
		groups = [
			SearchGroup(key=source.key, section=source.section, records=source.search(self.event, term))
			for source in self.sources
		]
		return EventSearchResponse(groups=[group for group in groups if group.records])
