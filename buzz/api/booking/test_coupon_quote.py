from frappe.utils import add_days, today

from buzz.api.booking import get_discount
from buzz.api.booking.details import coupon_code_of
from buzz.api.booking.schemas import DiscountQuoteRequest
from buzz.tests.base_test_cases import CouponTestCase, attendee_rows, create_paid_ticket_type
from buzz.tests.factories import (
	BuzzCouponCodeFactory,
	BuzzEventFactory,
	EventBookingFactory,
	EventTicketTypeFactory,
)

INVALID = "Invalid or expired code"


class QuoteTestCase(CouponTestCase):
	def quote(self, count: int = 1, **values) -> dict:
		ticket_types = [str(self.ticket_type.name)] * count
		request = DiscountQuoteRequest(
			event=str(self.event.name), currency="INR", ticket_types=ticket_types, **values
		)
		return get_discount(request).__json__()


class TestCouponQuote(QuoteTestCase):
	def test_no_coupons_quotes_zero(self):
		self.assertEqual(
			self.quote(), {"discount_amount": 0, "coupon_code": None, "error": None, "offer_name": None}
		)

	def test_promo_code_quote(self):
		self.create_coupon(code="QUOTE20", discount_percentage=20)

		self.assertEqual(
			self.quote(2, coupon_code="quote20"),
			{"discount_amount": 200, "coupon_code": "QUOTE20", "error": None, "offer_name": None},
		)

	def test_unknown_disabled_expired_and_other_event_codes_share_one_message(self):
		self.create_coupon(code="OFF", enabled=0)
		self.create_coupon(code="OLD", expires_on=add_days(today(), -1))
		BuzzCouponCodeFactory.create(code="ELSEWHERE")

		for code in ("NOPE", "OFF", "OLD", "ELSEWHERE"):
			self.assertEqual(
				self.quote(coupon_code=code),
				{"discount_amount": 0, "coupon_code": None, "error": INVALID, "offer_name": None},
			)

	def test_specific_message_once_code_is_real(self):
		self.create_coupon(code="TWOPLUS", minimum_requirement="Minimum Ticket Count", minimum_ticket_count=2)

		error = self.quote(coupon_code="TWOPLUS")["error"]

		self.assertIn("at least 2", error)

	def test_expiry_day_is_usable_in_quote(self):
		self.create_coupon(code="LASTDAY", expires_on=today())

		self.assertEqual(self.quote(coupon_code="LASTDAY")["discount_amount"], 50)

	def test_quote_respects_once_per_buyer(self):
		coupon = self.create_coupon(code="ONCE", once_per_buyer=1)
		self.create_booking(coupon.name, buyer_email="quote@example.com").submit()

		self.assertTrue(self.quote(coupon_code="ONCE", buyer_email="QUOTE@example.com")["error"])
		self.assertFalse(self.quote(coupon_code="ONCE", buyer_email="other@example.com")["error"])


class TestAutomaticCouponSelection(QuoteTestCase):
	def setUp(self):
		self.event = BuzzEventFactory.create()
		self.ticket_type = create_paid_ticket_type(self.event.name)

	def test_best_automatic_is_picked_and_promo_beats_it(self):
		self.create_coupon("automatic", discount_percentage=10)
		self.create_coupon("automatic", discount_percentage=40, code="Forty off")
		self.create_coupon(code="SMALL", discount_percentage=5)

		self.assertEqual(
			self.quote(),
			{"discount_amount": 200, "coupon_code": None, "error": None, "offer_name": "Forty off"},
		)
		self.assertEqual(self.quote(coupon_code="SMALL")["discount_amount"], 25)

	def test_tie_picks_oldest_and_booking_stores_it(self):
		oldest = self.create_coupon("automatic", discount_percentage=40).name
		self.create_coupon("automatic", discount_percentage=40)

		booking = self.create_booking()

		self.assertEqual((booking.coupon_code, booking.discount_amount), (oldest, 200))

	def test_automatic_ignores_a_free_order(self):
		self.create_coupon("automatic")
		self.ticket_type = EventTicketTypeFactory.create(event=self.event.name)

		self.assertIsNone(self.create_booking().coupon_code)

	def test_quote_names_the_automatic_offer(self):
		self.create_coupon("automatic", code="Group of 5+", discount_percentage=40)

		self.assertEqual(self.quote()["offer_name"], "Group of 5+")

	def test_receipt_names_the_automatic_offer(self):
		self.create_coupon("automatic", code="Group of 5+")

		self.assertEqual(coupon_code_of(self.create_booking()), "Group of 5+")


class TestAccessCodeQuote(QuoteTestCase):
	def setUp(self):
		super().setUp()
		self.hidden = EventTicketTypeFactory.create("is_hidden", event=self.event.name)
		self.ticket_types = [{"ticket_type": self.hidden.name}]

	def test_applies_before_its_hidden_tickets_are_in_the_cart(self):
		self.create_coupon("access_code", code="INSIDER", ticket_types=self.ticket_types)

		quote = self.quote(coupon_code="insider")

		self.assertEqual((quote["coupon_code"], quote["error"]), ("INSIDER", None))

	def test_a_used_up_access_code_gets_the_generic_message(self):
		code = self.create_coupon(
			"access_code", code="ONCEVIP", usage_limit=1, ticket_types=self.ticket_types
		)
		EventBookingFactory.create(
			event=self.event.name,
			buyer_email="first@example.com",
			access_code=code.name,
			attendees=attendee_rows(self.hidden.name, 1),
		).submit()

		self.assertEqual(self.quote(coupon_code="ONCEVIP")["error"], INVALID)

	def test_hidden_tickets_are_left_out_of_the_cart_without_their_code(self):
		hidden = EventTicketTypeFactory.create(
			"is_hidden", event=self.event.name, prices=[{"currency": "INR", "price": 500}]
		)
		self.create_coupon("automatic")
		request = DiscountQuoteRequest(
			event=str(self.event.name), currency="INR", ticket_types=[str(hidden.name)]
		)

		self.assertEqual(get_discount(request).discount_amount, 0)
