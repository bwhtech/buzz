import frappe

from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import default_currency

OLD_FIELDS = (
	"name",
	"coupon_type",
	"event",
	"is_active",
	"discount_type",
	"discount_value",
	"maximum_discount_amount",
	"minimum_order_value",
	"max_usage_count",
	"max_usage_per_user",
	"valid_till",
	"ticket_type",
)


def execute():
	# The dropped fields keep their columns after the model sync, so the old values are still readable.
	if not frappe.db.has_column("Buzz Coupon Code", "is_active"):
		return
	coupon = frappe.qb.DocType("Buzz Coupon Code")
	for row in frappe.qb.from_(coupon).select(*OLD_FIELDS).run(as_dict=True):
		if row.event:
			restructure(row)
		elif frappe.db.exists("Event Booking", {"coupon_code": row.name}):
			values = {"coupon_type": "Promo Code", "enabled": 0}
			frappe.db.set_value("Buzz Coupon Code", row.name, values, update_modified=False)
		else:
			frappe.delete_doc("Buzz Coupon Code", row.name, force=True, ignore_permissions=True)


def restructure(row):
	doc = frappe.get_doc("Buzz Coupon Code", row.name)
	doc.update(
		{
			"coupon_type": "Promo Code",
			"enabled": row.is_active,
			"usage_limit": row.max_usage_count,
			"once_per_buyer": int((row.max_usage_per_user or 0) > 0),
			"expires_on": row.valid_till,
		}
	)
	currency = default_currency(row.event)
	set_discount(doc, row, currency)
	set_minimum(doc, row, currency)
	doc.flags.ignore_validate = True
	doc.flags.ignore_mandatory = True
	doc.save(ignore_permissions=True)


def set_discount(doc, row, currency: str):
	if row.coupon_type == "Free Tickets":
		# The old limit counted tickets and the new one counts bookings, so organizers review these.
		doc.update({"discount_type": "Percentage", "discount_percentage": 100, "enabled": 0})
		doc.update({"applies_to_all_ticket_types": 0, "ticket_types": [{"ticket_type": row.ticket_type}]})
	elif row.discount_type == "Flat Amount":
		doc.discount_type = "Flat Amount"
		doc.set("discount_amounts", [{"currency": currency, "price": row.discount_value}])
	else:
		doc.update({"discount_type": "Percentage", "discount_percentage": row.discount_value})
		if row.maximum_discount_amount:
			doc.enabled = 0


def set_minimum(doc, row, currency: str):
	if row.coupon_type != "Free Tickets" and row.minimum_order_value:
		doc.minimum_requirement = "Minimum Order Amount"
		doc.set("minimum_order_amounts", [{"currency": currency, "price": row.minimum_order_value}])
