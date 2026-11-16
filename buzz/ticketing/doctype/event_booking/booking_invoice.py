from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, format_date, format_datetime, get_url, getdate

from buzz.emails import WORDMARK
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import get_team_settings

if TYPE_CHECKING:
	from buzz.ticketing.doctype.event_booking.event_booking import EventBooking

MINUS_SIGN = "\N{MINUS SIGN}"
DATE_FORMAT = "d MMM yyyy"
# wkhtmltopdf ignores most CSS page-break rules, so the template breaks pages itself.
# Budgets are in table rows; a line whose description wraps costs two.
FIRST_PAGE_ROWS = 24
PAGE_ROWS = 36
TOTALS_ROWS = 15
WRAPPING_DESCRIPTION_LENGTH = 80


class BookingInvoice:
	"""Everything the booking invoice template displays, fetched in a few queries."""

	def __init__(self, booking: "EventBooking"):
		self.booking = booking
		self.event = frappe.get_cached_doc("Buzz Event", booking.event)
		self.team = frappe.get_cached_doc("Buzz Team", self.event.team)
		self.settings = get_team_settings(self.event.team)

	def context(self) -> dict:
		lines = self.lines()
		return {
			"title": self.title(),
			"number": self.booking.name,
			"date": format_date(self.booking.creation, DATE_FORMAT),
			"payment_status": self.booking.payment_status,
			"payment": self.payment(),
			"seller": self.seller(),
			"buyer": self.buyer(),
			"event": self.event_details(),
			"lines": lines,
			"pages": self.paginate(lines),
			"totals": self.totals(),
			"total": self.total(),
			"tax_note": self.tax_note(),
			"support_email": self.settings.support_email,
			"brand": self.brand(),
			"booking_url": get_url(f"/b/account/bookings/{self.booking.name}"),
		}

	def brand(self) -> dict:
		website = frappe.get_cached_doc("Website Settings")
		logo = frappe.db.get_single_value("Buzz Settings", "app_logo") or website.app_logo
		return {"logo": logo or website.banner_image or WORDMARK, "name": website.app_name or "Buzz"}

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
			"display_name": booking.business_name or booking.buyer_name or booking.buyer_email,
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
		return {"title": self.event.title, "dates": self.event_dates(), "venue": self.event.get_venue_name()}

	def event_dates(self) -> str:
		start, end = getdate(self.event.start_date), getdate(self.event.end_date or self.event.start_date)
		if start == end:
			return format_date(start, DATE_FORMAT)
		if start.year != end.year:
			start_format = DATE_FORMAT
		else:
			start_format = "d" if start.month == end.month else "d MMM"
		return f"{format_date(start, start_format)} \N{EN DASH} {format_date(end, DATE_FORMAT)}"

	def payment(self) -> dict:
		latest = self.latest_payment()
		if not latest:
			return {"gateway": self.payment_method(), "reference": None, "paid_on": None}
		return {
			"gateway": latest.payment_gateway,
			"reference": latest.payment_id,
			"paid_on": format_datetime(latest.creation, "d MMM yyyy, h:mm a"),
		}

	def latest_payment(self):
		rows = frappe.get_all(
			"Event Payment",
			filters={
				"reference_doctype": "Event Booking",
				"reference_docname": self.booking.name,
				"payment_received": 1,
			},
			fields=["payment_gateway", "payment_id", "creation"],
			order_by="creation desc",
			limit=1,
		)
		return rows[0] if rows else None

	def payment_method(self) -> str | None:
		return self.booking.offline_payment_method or self.booking.payment_method

	def total(self) -> str:
		return self.money(self.booking.total_amount)

	@staticmethod
	def paginate(lines: list[dict]) -> list[dict]:
		"""Line items split into printed pages; totals move to their own page when they don't fit."""
		pages, rows, budget = [[]], 0, FIRST_PAGE_ROWS
		for line in lines:
			cost = 2 if len(line["description"]) > WRAPPING_DESCRIPTION_LENGTH else 1
			if rows + cost > budget:
				pages.append([])
				rows, budget = 0, PAGE_ROWS
			pages[-1].append(line)
			rows += cost
		if rows + TOTALS_ROWS > budget:
			pages.append([])
		return [{"lines": lines, "is_first": index == 0} for index, lines in enumerate(pages)]

	def lines(self) -> list[dict]:
		return [
			{**line, "unit_price": self.money(line["unit_price"]), "amount": self.money(line["amount"])}
			for line in self.ticket_type_lines() + self.add_on_lines()
		]

	def new_line(self, description: str, unit_price: float) -> dict:
		return {
			"description": description,
			"quantity": 0,
			"unit_price": flt(unit_price),
			"amount": 0,
		}

	def ticket_type_lines(self) -> list[dict]:
		titles = self.ticket_type_titles()
		lines: dict[str, dict] = {}
		for attendee in self.booking.attendees:
			key = str(attendee.ticket_type)
			line = lines.setdefault(key, self.new_line(titles.get(key, key), attendee.amount))
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
			description = self.add_on_description(row)
			line = lines.setdefault((description, flt(row.price)), self.new_line(description, row.price))
			line["quantity"] += 1
			line["amount"] += flt(row.price)
		return list(lines.values())

	def add_on_description(self, row) -> str:
		return f"{row.title} ({row.value})" if row.user_selects_option and row.value else row.title

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
		return {"label": label, "amount": self.signed_money(amount), "is_total": is_total}

	def signed_money(self, amount: float) -> str:
		formatted = self.money(abs(flt(amount)))
		return f"{MINUS_SIGN}{formatted}" if flt(amount) < 0 else formatted

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
		currency = self.booking.currency
		number_format = frappe.db.get_value("Currency", currency, "number_format", cache=True)
		return fmt_money(amount, currency=currency, format=number_format or None)
