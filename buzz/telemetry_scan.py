from statistics import median

import frappe
from frappe.query_builder import Case, DocType
from frappe.query_builder.functions import Count, IfNull, Max, Min, Sum
from frappe.utils import add_days, date_diff, getdate, today
from frappe.utils.telemetry.pulse.client import is_enabled

from buzz import telemetry
from buzz.api.booking.services import OFFLINE_PAYMENT_METHOD

RECORD_COUNTS = {
	"ticket_types": ("Event Ticket Type", {}),
	"add_ons": ("Ticket Add-on", {}),
	"coupons": ("Buzz Coupon Code", {}),
	"event_templates": ("Event Template", {}),
	"custom_fields": ("Buzz Custom Field", {}),
	"offline_payment_methods": ("Offline Payment Method", {}),
	"tickets_issued": ("Event Ticket", {"docstatus": 1}),
	"check_ins": ("Event Check In", {"docstatus": 1}),
	"talk_proposals": ("Talk Proposal", {}),
	"event_proposals": ("Event Proposal", {}),
	"sponsorship_enquiries": ("Sponsorship Enquiry", {}),
	"sponsors": ("Event Sponsor", {}),
	"cancellations": ("Ticket Cancellation Request", {"docstatus": 1}),
	"refunds_processed": ("Event Booking Refund", {"status": "Processed"}),
}


def send_site_profile():
	if not is_enabled():
		return

	telemetry.capture("site_profile", get_site_profile())


def get_site_profile() -> dict:
	return {
		**get_event_profile(),
		**get_booking_profile(),
		**get_bookings_per_event(),
		**get_record_counts(),
		"payment_gateways": count_payment_gateways(),
	}


def count_where(condition):
	return Sum(Case().when(condition, 1).else_(0))


def days_since(timestamp) -> int | None:
	return date_diff(today(), getdate(timestamp)) if timestamp else None


def get_event_profile() -> dict:
	empty = {
		"events": 0,
		"events_published": 0,
		"events_upcoming": 0,
		"events_online": 0,
		"events_from_proposal": 0,
		"first_event_days_ago": None,
		"last_event_days_ago": None,
	}
	try:
		event = DocType("Buzz Event")
		row = (
			frappe.qb.from_(event)
			.select(
				Count(event.name),
				count_where(event.is_published == 1),
				count_where(event.start_date >= today()),
				count_where(event.medium == "Online"),
				count_where(IfNull(event.proposal, "") != ""),
				Min(event.creation),
				Max(event.creation),
			)
			.run()[0]
		)
	except Exception:
		return empty

	return {
		"events": row[0] or 0,
		"events_published": int(row[1] or 0),
		"events_upcoming": int(row[2] or 0),
		"events_online": int(row[3] or 0),
		"events_from_proposal": int(row[4] or 0),
		"first_event_days_ago": days_since(row[5]),
		"last_event_days_ago": days_since(row[6]),
	}


def get_booking_profile() -> dict:
	empty = {
		"bookings": 0,
		"bookings_offline": 0,
		"bookings_paid": 0,
		"bookings_last_30_days": 0,
		"last_booking_days_ago": None,
	}
	try:
		booking = DocType("Event Booking")
		row = (
			frappe.qb.from_(booking)
			.select(
				Count(booking.name),
				count_where(booking.payment_method == OFFLINE_PAYMENT_METHOD),
				count_where(booking.total_amount > 0),
				count_where(booking.creation >= add_days(today(), -30)),
				Max(booking.creation),
			)
			.where(booking.docstatus == 1)
			.run()[0]
		)
	except Exception:
		return empty

	return {
		"bookings": row[0] or 0,
		"bookings_offline": int(row[1] or 0),
		"bookings_paid": int(row[2] or 0),
		"bookings_last_30_days": int(row[3] or 0),
		"last_booking_days_ago": days_since(row[4]),
	}


def get_bookings_per_event() -> dict:
	try:
		booking = DocType("Event Booking")
		counts = (
			frappe.qb.from_(booking)
			.select(Count(booking.name))
			.where(booking.docstatus == 1)
			.groupby(booking.event)
			.run(pluck=True)
		)
	except Exception:
		counts = []

	return {
		"bookings_per_event_median": median(counts) if counts else 0,
		"bookings_per_event_max": max(counts, default=0),
	}


def get_record_counts() -> dict:
	counts = {}
	for key, (doctype, filters) in RECORD_COUNTS.items():
		try:
			counts[key] = frappe.db.count(doctype, filters)
		except Exception:
			counts[key] = 0
	return counts


def count_payment_gateways() -> int:
	try:
		return len(
			frappe.get_all(
				"Event Payment Gateway",
				filters={"parenttype": "Buzz Event"},
				pluck="payment_gateway",
				distinct=True,
			)
		)
	except Exception:
		return 0
