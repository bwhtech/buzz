from collections.abc import Callable
from dataclasses import dataclass

import frappe
from frappe.utils import format_time

from buzz.api.events.services import guest_search_filters
from buzz.api.proposals.services import proposal_search_filters
from buzz.api.search.schemas import SearchRecord
from buzz.api.sponsorships.enquiries import search_filters as sponsor_search_filters

RECORDS_PER_GROUP = 3


def like_filters(*fields: str) -> Callable[[str], list[list]]:
	return lambda term: [[field, "like", f"%{term}%"] for field in fields]


def event_filters(event: str) -> list[list]:
	return [["event", "=", event]]


def schedule_item_filters(event: str) -> list[list]:
	schedules = frappe.get_all("Buzz Schedule", filters={"event": event}, pluck="name")
	return [["parenttype", "=", "Buzz Schedule"], ["parent", "in", schedules]]


@dataclass(frozen=True)
class SearchSource:
	key: str
	section: str
	doctype: str
	title_field: str
	subtitle_field: str | None
	search_filters: Callable[[str], list[list] | None]
	base_filters: Callable[[str], list[list]] = event_filters
	format_subtitle: Callable[[object], str] = str

	def search(self, event: str, term: str) -> list[SearchRecord]:
		fields = [field for field in ("name", self.title_field, self.subtitle_field) if field]
		rows = frappe.get_all(
			self.doctype,
			filters=self.base_filters(event),
			or_filters=self.search_filters(term),
			fields=fields,
			limit_page_length=RECORDS_PER_GROUP,
			ignore_permissions=True,
		)
		return [self.record(row) for row in rows]

	def record(self, row) -> SearchRecord:
		subtitle = row.get(self.subtitle_field) if self.subtitle_field else None
		return SearchRecord(
			name=str(row.name),
			title=str(row.get(self.title_field) or row.name),
			subtitle=self.format_subtitle(subtitle) if subtitle else None,
		)


def submitted_guest_filters(event: str) -> list[list]:
	return [*event_filters(event), ["docstatus", "=", 1]]


SOURCES = (
	SearchSource(
		"guests",
		"guests",
		"Event Ticket",
		"attendee_name",
		"attendee_email",
		guest_search_filters,
		submitted_guest_filters,
	),
	SearchSource("talks", "talks", "Talk Proposal", "title", "status", proposal_search_filters),
	SearchSource("sponsors", "sponsors", "Event Sponsor", "company_name", "website", sponsor_search_filters),
	SearchSource("coupons", "ticketing", "Buzz Coupon Code", "code", "description", like_filters("code")),
	SearchSource(
		"schedule",
		"talks",
		"Buzz Schedule Item",
		"title",
		"start_time",
		like_filters("title"),
		schedule_item_filters,
		lambda start: format_time(start, "HH:mm"),
	),
	SearchSource(
		"communications",
		"communications",
		"Event Communication",
		"subject",
		"audience",
		like_filters("subject"),
	),
)
