import frappe
from frappe.utils import fmt_money

from buzz.api.booking.services import create_add_on_doc
from buzz.tests.base_test_cases import BookingTestCase
from buzz.tests.factories import (
	BuzzCouponCodeFactory,
	BuzzTeamFactory,
	EventBookingFactory,
	EventTicketTypeFactory,
	TicketAddOnFactory,
)

SELLER_TAX_ID = "27AAAAA0000A1Z5"
BUYER_TAX_ID = "29BBBBB1111B1Z6"
TICKET_PRICE = 500
ADD_ON_PRICE = 150


def money(amount: float) -> str:
	return fmt_money(amount, currency="INR")


class TestBookingInvoice(BookingTestCase):
	def setUp(self):
		super().setUp()
		self.set_event({"apply_tax": 0, "tax_inclusive": 0, "tax_label": None, "tax_percentage": 0})
		self.set_seller(legal_name="Acme Events Pvt Ltd", tax_id=SELLER_TAX_ID, billing_address="1 MG Road")
		self.ticket_type = EventTicketTypeFactory.create("paid", event=self.event.name).name

	def set_seller(self, **values):
		BuzzTeamFactory.set_settings(self.event.team, values)

	def set_tax(self, label: str, percentage: int, inclusive: int = 0):
		self.set_event(
			{"apply_tax": 1, "tax_label": label, "tax_percentage": percentage, "tax_inclusive": inclusive}
		)

	def create_invoice_booking(self, count: int = 2, add_on_option: str | None = None, **overrides):
		attendees = [
			{
				"ticket_type": self.ticket_type,
				"first_name": f"Guest{index}",
				"email": f"guest{index}@example.com",
			}
			for index in range(count)
		]
		if add_on_option:
			add_on = TicketAddOnFactory.create(event=self.event.name, price=ADD_ON_PRICE).name
			attendees[0]["add_ons"] = create_add_on_doc("", [{"add_on": add_on, "value": add_on_option}]).name
		details = {
			"invoice_requested": 1,
			"tax_id": BUYER_TAX_ID,
			"business_name": "Globex Corporation",
			"billing_address": "22 Park Street",
			"billing_state": "Karnataka",
		}
		return EventBookingFactory.create(
			event=self.event.name, attendees=attendees, **{**details, **overrides}
		)

	def test_ticket_types_are_one_line_with_quantity(self):
		invoice = self.create_invoice_booking(count=2).get_invoice()

		self.assertEqual(
			invoice["lines"],
			[
				{
					"description": frappe.db.get_value("Event Ticket Type", self.ticket_type, "title"),
					"quantity": 2,
					"unit_price": money(TICKET_PRICE),
					"amount": money(2 * TICKET_PRICE),
				}
			],
		)

	def test_add_ons_are_their_own_lines(self):
		invoice = self.create_invoice_booking(count=2, add_on_option="XL").get_invoice()

		add_on_line = invoice["lines"][1]
		self.assertEqual(add_on_line["quantity"], 1)
		self.assertEqual(add_on_line["amount"], money(ADD_ON_PRICE))
		self.assertEqual(invoice["totals"][0]["amount"], money(2 * TICKET_PRICE + ADD_ON_PRICE))

	def test_a_discount_is_one_row_that_names_the_coupon(self):
		coupon = BuzzCouponCodeFactory.create("flat", event=self.event.name)
		booking = self.create_invoice_booking(count=2, coupon_code=coupon.name)

		totals = booking.get_invoice()["totals"]

		self.assertEqual(totals[0]["amount"], money(2 * TICKET_PRICE))
		self.assertEqual(totals[1]["label"], f"Discount ({coupon.code})")
		self.assertEqual(totals[1]["amount"], money(-100))
		self.assertEqual(totals[-1]["amount"], money(2 * TICKET_PRICE - 100))

	def test_lines_add_up_to_the_subtotal_when_a_coupon_applies(self):
		coupon = BuzzCouponCodeFactory.create("flat", event=self.event.name)
		invoice = self.create_invoice_booking(count=2, coupon_code=coupon.name).get_invoice()

		self.assertEqual(invoice["lines"][0]["amount"], invoice["totals"][0]["amount"])

	def test_exclusive_tax_is_added_below_the_subtotal(self):
		self.set_tax("GST", 18)

		invoice = self.create_invoice_booking(count=1).get_invoice()

		self.assertEqual(
			[(row["label"], row["amount"]) for row in invoice["totals"]],
			[
				("Subtotal", money(TICKET_PRICE)),
				("GST (18%)", money(TICKET_PRICE * 0.18)),
				("Total", money(TICKET_PRICE * 1.18)),
			],
		)
		self.assertIsNone(invoice["tax_note"])

	def test_inclusive_tax_is_a_note_under_the_total(self):
		self.set_tax("GST", 18, inclusive=1)

		invoice = self.create_invoice_booking(count=1).get_invoice()

		self.assertEqual([row["label"] for row in invoice["totals"]], ["Subtotal", "Total"])
		self.assertEqual(invoice["tax_note"], f"Includes GST of {money(round(TICKET_PRICE * 18 / 118, 2))}")

	def test_title_is_tax_invoice_only_when_the_seller_has_a_tax_id_and_tax_applies(self):
		self.set_tax("GST", 18)
		self.assertEqual(self.create_invoice_booking().get_invoice()["title"], "Tax Invoice")

		self.set_seller(tax_id=None)
		self.assertEqual(self.create_invoice_booking().get_invoice()["title"], "Invoice")

	def test_gst_uses_gstin_and_place_of_supply(self):
		self.set_tax("GST", 18)

		invoice = self.create_invoice_booking().get_invoice()

		self.assertEqual(invoice["seller"]["tax_id_label"], "GSTIN")
		self.assertEqual(invoice["buyer"]["tax_id_label"], "GSTIN")
		self.assertEqual(invoice["buyer"]["state_label"], "Place of supply")

	def test_other_taxes_are_labelled_by_their_name(self):
		self.set_tax("VAT", 20)

		invoice = self.create_invoice_booking().get_invoice()

		self.assertEqual(invoice["buyer"]["tax_id_label"], "VAT number")
		self.assertEqual(invoice["buyer"]["state_label"], "State / region")

	def test_seller_is_the_team_legal_name_and_buyer_the_business(self):
		invoice = self.create_invoice_booking().get_invoice()

		self.assertEqual(invoice["seller"]["name"], "Acme Events Pvt Ltd")
		self.assertEqual(invoice["seller"]["tax_id"], SELLER_TAX_ID)
		self.assertEqual(invoice["buyer"]["name"], "Globex Corporation")
		self.assertEqual(invoice["buyer"]["tax_id"], BUYER_TAX_ID)

	def test_seller_falls_back_to_the_team_name(self):
		self.set_seller(legal_name=None)

		invoice = self.create_invoice_booking().get_invoice()

		self.assertEqual(
			invoice["seller"]["name"], frappe.db.get_value("Buzz Team", self.event.team, "team_name")
		)

	def test_refunds_add_refunded_and_net_paid_rows(self):
		booking = self.create_invoice_booking(count=1)
		booking.refunded_amount = 200

		totals = booking.get_invoice()["totals"]

		self.assertEqual(totals[-2], {"label": "Refunded", "amount": money(-200), "is_total": False})
		self.assertEqual(totals[-1]["label"], "Net paid")
		self.assertEqual(totals[-1]["amount"], money(TICKET_PRICE - 200))

	def test_printed_html_carries_the_references_and_a_line_item(self):
		booking = self.create_invoice_booking(count=1)
		booking.submit()

		html = frappe.get_print("Event Booking", booking.name, "Booking Invoice", as_pdf=False)

		ticket_title = frappe.db.get_value("Event Ticket Type", self.ticket_type, "title")
		for expected in (booking.name, SELLER_TAX_ID, BUYER_TAX_ID, ticket_title):
			self.assertIn(expected, html)
