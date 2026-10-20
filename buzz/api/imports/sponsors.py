from typing import ClassVar

import frappe
from frappe import _
from frappe.utils import validate_email_address

from buzz.api.imports.schemas import ImportOption
from buzz.api.imports.services import Field, Importer


class SponsorImporter(Importer):
	"""One row is a sponsor on one of the event's tiers. A logo is optional, given as a link."""

	section = "sponsors"
	noun = "sponsors"
	fields: ClassVar[dict[str, Field]] = {
		"company_name": Field(
			"Company Name", True, ("company", "name", "sponsor", "sponsor_name", "organisation")
		),
		"tier": Field("Tier", True, ("level", "sponsorship_tier", "package", "plan")),
		"website": Field("Website", aliases=("url", "site", "web")),
		"country": Field("Country"),
		"contact_email": Field("Contact Email", aliases=("email", "contact", "e_mail")),
		"company_logo": Field("Logo URL", aliases=("logo", "company_logo", "logo_link", "image")),
	}
	value_fields: ClassVar[dict[str, bool]] = {"tier": False, "country": False}

	def options(self, field: str) -> list[ImportOption]:
		if field == "tier":
			tiers = frappe.get_all(
				"Sponsorship Tier", filters={"event": self.event}, fields=["name", "title"]
			)
			return [ImportOption(value=tier.name, label=tier.title) for tier in tiers]
		return [ImportOption(value=name, label=name) for name in frappe.get_all("Country", pluck="name")]

	def row_error(self, record: dict) -> str | None:
		if error := super().row_error(record):
			return error
		email = record.get("contact_email")
		if email and not validate_email_address(email):
			return _("{0} isn't an email.").format(email)
		logo = record.get("company_logo")
		if logo and not logo.startswith(("http://", "https://", "/files/")):
			return _("The logo {0} isn't a link.").format(logo)
		return None

	def duplicate_keys(self, record: dict) -> list[str]:
		return [record["company_name"].lower()]

	def existing_keys(self) -> set[str]:
		names = frappe.get_all("Event Sponsor", filters={"event": self.event}, pluck="company_name")
		return {name.lower() for name in names}

	def notes(self) -> list[str]:
		notes = super().notes()
		without_logo = sum(1 for record in self.sorted_records[0] if not record.get("company_logo"))
		if without_logo:
			notes.append(
				_("Without a logo, so they show their name until one is added: {0}.").format(without_logo)
			)
		return notes

	def import_record(self, record: dict) -> None:
		frappe.get_doc(
			{
				"doctype": "Event Sponsor",
				"event": self.event,
				"company_name": record["company_name"],
				"tier": self.resolve("tier", record["tier"]),
				"website": record.get("website"),
				"country": self.resolve("country", record.get("country")),
				"contact_email": record.get("contact_email"),
				"company_logo": record.get("company_logo"),
			}
		).insert()
