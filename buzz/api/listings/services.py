from zoneinfo import ZoneInfo

import frappe
from frappe.utils import get_system_timezone

from buzz.api.communities.submissions import REQUEST, external_request
from buzz.api.listings.exceptions import NotAnIntegration
from buzz.api.listings.schemas import EventListing
from buzz.permissions import INTEGRATION_ROLE


class PartnerListings:
	"""Events a partner site lists on its own community page, as that team's integration user."""

	def __init__(self):
		filters = {"user": frappe.session.user, "team_role": INTEGRATION_ROLE, "enabled": 1}
		teams = frappe.get_all("Buzz Team Membership", filters=filters, pluck="team")
		if len(teams) != 1:
			NotAnIntegration.throw()
		self.community = teams[0]

	def find_request_name(self, source_id: str) -> str | None:
		return frappe.db.get_value(REQUEST, {"community": self.community, "source_id": source_id})

	def upsert(self, listing: EventListing) -> None:
		"""A request the community took down stays down; only its details follow the partner."""
		name = self.find_request_name(listing.source_id)
		request = frappe.get_doc(REQUEST, name) if name else self.new_request(listing)
		request.update(in_system_time_zone(listing.model_dump()))
		request.save(ignore_permissions=True)

	def new_request(self, listing: EventListing):
		request = external_request(self.community, listing)
		request.update({"status": "Approved", "reviewed_by": frappe.session.user})
		return request

	def remove(self, source_id: str) -> None:
		if name := self.find_request_name(source_id):
			frappe.delete_doc(REQUEST, name, ignore_permissions=True)


def in_system_time_zone(values: dict) -> dict:
	"""Datetime fields hold naive system time."""
	zone = ZoneInfo(get_system_timezone())
	for field in ("start_datetime", "end_datetime"):
		values[field] = values[field].astimezone(zone).replace(tzinfo=None)
	return values
