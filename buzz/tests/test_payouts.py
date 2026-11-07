from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import frappe
from bwh_payments import testing as payment_testing
from frappe.utils import add_days, get_datetime, get_system_timezone, getdate, today

from buzz.payments import get_payment_link_for_sponsorship
from buzz.payouts import PayoutSplit
from buzz.tests.base_test_cases import BookingRefundTestCase
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	SponsorshipEnquiryFactory,
	SponsorshipTierFactory,
)

PLATFORM_FEE = 10
# Two tickets of 500 plus 10% tax.
BOOKING_TOTAL = 1100
TEAM_SHARE = 990


def set_platform_fee(percent: float):
	frappe.db.set_single_value("Buzz Settings", "platform_fee_percent", percent)
	frappe.clear_document_cache("Buzz Settings", "Buzz Settings")


class PayoutTestCase(BookingRefundTestCase):
	"""The paid booking's team has an active linked account, and BWH keeps a 10% platform fee."""

	@classmethod
	def setUpClass(cls):
		cls.team = BuzzTeamFactory.create_owned_by().name
		super().setUpClass()
		cls.linked_account = payment_testing.create_test_linked_account("Buzz Team", cls.team, cls.gateway)

	@classmethod
	def create_event(cls) -> str:
		return BuzzEventFactory.create(
			"with_tax",
			tax_percentage=10,
			team=cls.team,
			end_time="18:00:00",
			time_zone=None,
			payment_gateways=[{"payment_gateway": cls.gateway}],
		).name

	def setUp(self):
		set_platform_fee(PLATFORM_FEE)
		self.addCleanup(set_platform_fee, 0)
		super().setUp()

	@property
	def payment_request(self):
		return frappe.get_doc("Gateway Payment Request", self.payment.payment_request)


class TestTeamPayouts(PayoutTestCase):
	def test_the_team_is_paid_the_total_less_the_platform_fee(self):
		splits = self.payment_request.splits

		self.assertEqual(self.booking.total_amount, BOOKING_TOTAL)
		self.assertEqual(
			[(split.linked_account, split.amount) for split in splits], [(self.linked_account, TEAM_SHARE)]
		)

	def test_the_share_is_held_until_two_days_after_the_event(self):
		end_date = frappe.db.get_value("Buzz Event", self.event, "end_date")
		event_end = datetime.combine(getdate(end_date), datetime.min.time().replace(hour=18))

		hold_until = get_datetime(self.payment_request.splits[0].hold_until)

		self.assertEqual(hold_until, event_end + timedelta(days=2))

	def test_a_half_refund_takes_back_half_the_teams_share(self):
		self.booking.refund(amount=550)

		self.assertEqual(payment_testing.get_reversed_amount(self.payment.payment_request), 495)

	def test_a_full_refund_takes_back_the_whole_share(self):
		self.booking.refund(amount=BOOKING_TOTAL)

		self.assertEqual(payment_testing.get_reversed_amount(self.payment.payment_request), TEAM_SHARE)

	def test_a_sponsorship_payment_pays_the_team_too(self):
		tier = SponsorshipTierFactory.create(event=self.event, prices=[{"currency": "INR", "price": 5000}])
		enquiry = SponsorshipEnquiryFactory.create(event=self.event, tier=tier.name)

		get_payment_link_for_sponsorship(enquiry.name, tier.name, payment_gateway=self.gateway)

		payment_request = frappe.get_last_doc("Gateway Payment Request", {"ref_docname": enquiry.name})
		self.assertEqual([split.amount for split in payment_request.splits], [4500])


class TestPayoutSplit(PayoutTestCase):
	def split_for(self, event: str | int, amount: float = 1000, currency: str = "INR") -> list[dict]:
		return PayoutSplit(event, amount, currency, self.gateway).as_list()

	def test_a_payout_follows_the_events_time_zone(self):
		end_date = add_days(today(), 20)
		event = BuzzEventFactory.create(
			team=self.team,
			start_date=end_date,
			end_date=end_date,
			end_time="18:00:00",
			time_zone="America/New_York",
		).name
		event_end = datetime.combine(getdate(end_date), datetime.min.time().replace(hour=18))
		expected = (
			event_end.replace(tzinfo=ZoneInfo("America/New_York"))
			.astimezone(ZoneInfo(get_system_timezone()))
			.replace(tzinfo=None)
		)

		self.assertEqual(self.split_for(event)[0]["hold_until"], expected + timedelta(days=2))

	def test_a_one_day_event_is_held_from_its_start_date(self):
		start_date = add_days(today(), 15)
		event = BuzzEventFactory.create(
			team=self.team, start_date=start_date, end_date=None, end_time="20:00:00", time_zone=None
		).name
		event_end = datetime.combine(getdate(start_date), datetime.min.time().replace(hour=20))

		self.assertEqual(self.split_for(event)[0]["hold_until"], event_end + timedelta(days=2))

	def test_no_platform_fee_means_no_payouts(self):
		set_platform_fee(0)

		self.assertEqual(self.split_for(self.event), [])

	def test_a_currency_the_gateway_cannot_split_is_collected_in_full(self):
		self.assertEqual(self.split_for(self.event, currency="USD"), [])

	def test_a_team_without_an_active_linked_account_is_collected_in_full(self):
		other_team = BuzzTeamFactory.create_owned_by().name
		event = BuzzEventFactory.create(team=other_team).name

		self.assertEqual(self.split_for(event), [])

	def test_the_fee_is_rounded_to_the_currencys_smallest_unit(self):
		self.assertEqual(self.split_for(self.event, amount=99.99)[0]["amount"], 89.99)


class TestPlatformFee(PayoutTestCase):
	def test_a_fee_below_razorpays_costs_is_refused(self):
		settings = frappe.get_doc("Buzz Settings")
		settings.platform_fee_percent = 2

		with self.assertRaisesRegex(frappe.ValidationError, "Platform Fee"):
			settings.save()

	def test_a_fee_of_zero_turns_payouts_off_and_saves(self):
		settings = frappe.get_doc("Buzz Settings")
		settings.platform_fee_percent = 0
		settings.save()

		self.assertEqual(frappe.db.get_single_value("Buzz Settings", "platform_fee_percent"), 0)


class TestPayoutHolds(PayoutTestCase):
	def test_moving_the_event_moves_the_hold_on_the_teams_share(self):
		self.addCleanup(frappe.clear_document_cache, "Buzz Event", self.event)
		event = frappe.get_doc("Buzz Event", self.event)
		new_end_date = add_days(event.end_date, 7)
		event.end_date = new_end_date
		event.save()

		hold_until = get_datetime(self.payment_request.splits[0].hold_until)

		event_end = datetime.combine(getdate(new_end_date), datetime.min.time().replace(hour=18))
		self.assertEqual(hold_until, event_end + timedelta(days=2))
