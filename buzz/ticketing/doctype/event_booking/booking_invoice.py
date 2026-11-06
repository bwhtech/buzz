from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, format_date

from buzz.events.doctype.buzz_team_settings.buzz_team_settings import get_team_settings

if TYPE_CHECKING:
	from buzz.ticketing.doctype.event_booking.event_booking import EventBooking


class BookingInvoice:
	"""Everything the booking invoice template displays, fetched in a few queries."""

	def __init__(self, booking: "EventBooking"):
		self.booking = booking
		self.event = frappe.get_cached_doc("Buzz Event", booking.event)
		self.team = frappe.get_cached_doc("Buzz Team", self.event.team)
		self.settings = get_team_settings(self.event.team)

	def context(self) -> dict:
		return {
			"title": self.title(),
			"number": self.booking.name,
			"date": format_date(self.booking.creation),
			"payment_status": self.booking.payment_status,
			"payment_method": self.booking.offline_payment_method or self.booking.payment_method,
			"seller": self.seller(),
			"buyer": self.buyer(),
			"event": self.event_details(),
			"lines": self.lines(),
			"totals": self.totals(),
			"tax_note": self.tax_note(),
			"support_email": self.settings.support_email,
		}

	def title(self) -> str:
		is_tax_invoice = self.settings.tax_id and self.booking.tax_amount
		return _("Tax Invoice") if is_tax_invoice else _("Invoice")

	def seller(self) -> dict:
		return {
			"logo": self.team.logo,
			"name": self.settings.legal_name or self.team.team_name,
			"address": self.settings.billing_address,
			"tax_id": self.settings.tax_id,
			"tax_id_label": self.tax_id_label(),
		}

	def buyer(self) -> dict:
		booking = self.booking
		return {
			"name": booking.business_name,
			"contact_name": booking.buyer_name,
			"address": booking.billing_address,
			"state": booking.billing_state,
			"state_label": _("Place of supply") if self.is_gst() else _("State / region"),
			"tax_id": booking.tax_id,
			"tax_id_label": self.tax_id_label(),
			"email": booking.buyer_email,
			"phone": booking.buyer_phone,
		}

	def is_gst(self) -> bool:
		return (self.booking.tax_label or "").strip().upper() == "GST"

	def tax_id_label(self) -> str:
		return "GSTIN" if self.is_gst() else _("{0} number").format(_(self.booking.tax_label or "Tax"))

	def event_details(self) -> dict:
		start, end = self.event.start_date, self.event.end_date
		dates = (
			format_date(start) if not end or end == start else f"{format_date(start)} - {format_date(end)}"
		)
		return {"title": self.event.title, "dates": dates, "venue": self.event.get_venue_name()}

	def lines(self) -> list[dict]:
		return [
			{**line, "unit_price": self.money(line["unit_price"]), "amount": self.money(line["amount"])}
			for line in self.ticket_type_lines() + self.add_on_lines()
		]

	def ticket_type_lines(self) -> list[dict]:
		titles = self.ticket_type_titles()
		lines: dict[str, dict] = {}
		for attendee in self.booking.attendees:
			key = str(attendee.ticket_type)
			line = lines.setdefault(
				key,
				{
					"description": titles.get(key, key),
					"quantity": 0,
					"unit_price": flt(attendee.amount),
					"amount": 0,
				},
			)
			line["quantity"] += 1
			line["amount"] += flt(attendee.amount)
		return list(lines.values())

	def ticket_type_titles(self) -> dict[str, str]:
		ids = {attendee.ticket_type for attendee in self.booking.attendees}
		rows = frappe.get_all(
			"Event Ticket Type", filters={"name": ("in", list(ids))}, fields=["name", "title"]
		)
		return {str(row.name): row.title for row in rows}

	def add_on_lines(self) -> list[dict]:
		lines: dict[tuple, dict] = {}
		for row in self.add_on_rows():
			description = f"{row.title} ({row.value})" if row.user_selects_option and row.value else row.title
			line = lines.setdefault(
				(description, flt(row.price)),
				{"description": description, "quantity": 0, "unit_price": flt(row.price), "amount": 0},
			)
			line["quantity"] += 1
			line["amount"] += flt(row.price)
		return list(lines.values())

	def add_on_rows(self) -> list:
		parents = [attendee.add_ons for attendee in self.booking.attendees if attendee.add_ons]
		if not parents:
			return []
		return frappe.get_all(
			"Ticket Add-on Value",
			filters={"parent": ("in", parents)},
			fields=[
				"add_on.title as title",
				"add_on.user_selects_option as user_selects_option",
				"value",
				"price",
			],
			order_by="idx",
		)

	def totals(self) -> list[dict]:
		booking = self.booking
		rows = [self.total_row(_("Subtotal"), booking.net_amount)]
		if booking.discount_amount:
			rows.append(self.total_row(self.discount_label(), -flt(booking.discount_amount)))
		if booking.tax_amount and not self.is_tax_inclusive():
			rows.append(self.total_row(self.tax_label(), booking.tax_amount))
		rows.append(self.total_row(_("Total"), booking.total_amount, is_total=True))
		if booking.refunded_amount:
			rows.append(self.total_row(_("Refunded"), -flt(booking.refunded_amount)))
			rows.append(
				self.total_row(_("Net paid"), flt(booking.total_amount) - flt(booking.refunded_amount))
			)
		return rows

	def total_row(self, label: str, amount: float, is_total: bool = False) -> dict:
		return {"label": label, "amount": self.money(amount), "is_total": is_total}

	def discount_label(self) -> str:
		code = self.booking.coupon_code and frappe.db.get_value(
			"Buzz Coupon Code", self.booking.coupon_code, "code"
		)
		return _("Discount ({0})").format(code) if code else _("Discount")

	def tax_label(self) -> str:
		return f"{_(self.booking.tax_label or 'Tax')} ({flt(self.booking.tax_percentage):g}%)"

	def tax_note(self) -> str | None:
		if self.booking.tax_amount and self.is_tax_inclusive():
			return _("Includes {0} of {1}").format(
				_(self.booking.tax_label or "Tax"), self.money(self.booking.tax_amount)
			)

	def is_tax_inclusive(self) -> bool:
		# Same rule as the dashboard: inclusive tax is not added on top of net less discount.
		expected_total = flt(self.booking.net_amount) - flt(self.booking.discount_amount)
		return abs(flt(self.booking.total_amount) - expected_total) < 0.01

	def money(self, amount: float) -> str:
		return fmt_money(amount, currency=self.booking.currency)
