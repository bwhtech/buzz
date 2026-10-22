from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.events import get_event_coupons
from buzz.api.events.exceptions import CannotManageEvent
from buzz.tests.factories import (
	BuzzCouponCodeFactory,
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventBookingFactory,
	EventTicketTypeFactory,
	UserFactory,
)


class TestEventCoupons(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("coupons-owner@example.com").name
		cls.viewer = UserFactory.create_once("coupons-viewer@example.com").name
		cls.outsider = UserFactory.create_once("coupons-stranger@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name
		BuzzTeamMembershipFactory.create(team=cls.team, user=cls.viewer, team_role="Viewer")

	def setUp(self):
		self.event = str(BuzzEventFactory.create(team=self.team).name)
		self.ticket_type = str(
			EventTicketTypeFactory.create(event=self.event, prices=[{"currency": "INR", "price": 1000}]).name
		)

	def create_coupon(self, *traits, **overrides):
		return BuzzCouponCodeFactory.create(*traits, event=self.event, **overrides).name

	def redeem(self, coupon: str):
		attendees = [{"ticket_type": self.ticket_type, "first_name": "Buyer", "email": "buyer@example.com"}]
		EventBookingFactory.create(event=self.event, coupon_code=coupon, attendees=attendees).submit()

	def payload_as(self, user: str) -> dict:
		with self.set_user(user):
			return get_event_coupons(self.event).__json__()

	def coupon_in(self, payload: dict, name: str) -> dict:
		return next(coupon for coupon in payload["coupons"] if coupon["name"] == name)

	def test_lists_only_this_events_coupons(self):
		coupon = self.create_coupon(code="EARLYBIRD")
		BuzzCouponCodeFactory.create()

		payload = self.payload_as(self.owner)

		self.assertEqual([row["name"] for row in payload["coupons"]], [coupon])
		self.assertEqual(payload["coupons"][0]["code"], "EARLYBIRD")

	def test_counts_redemptions(self):
		coupon = self.create_coupon(usage_limit=5)
		self.redeem(coupon)
		self.redeem(coupon)

		row = self.coupon_in(self.payload_as(self.owner), coupon)

		self.assertEqual((row["times_used"], row["usage_limit"]), (2, 5))

	def test_status_follows_the_coupon_rules(self):
		active = self.create_coupon()
		disabled = self.create_coupon(enabled=0)
		ended = self.create_coupon(expires_on=add_days(today(), -1))
		used_up = self.create_coupon(usage_limit=1)
		self.redeem(used_up)

		payload = self.payload_as(self.owner)

		statuses = [self.coupon_in(payload, name)["status"] for name in (active, disabled, ended, used_up)]
		self.assertEqual(statuses, ["Active", "Disabled", "Ended", "Used up"])

	def test_coupon_before_its_start_is_scheduled(self):
		coupon = self.create_coupon(starts_on=add_days(today(), 3))

		self.assertEqual(self.coupon_in(self.payload_as(self.owner), coupon)["status"], "Scheduled")

	def test_automatic_coupon_carries_its_name(self):
		coupon = self.create_coupon("automatic", code="Group of 5+")

		self.assertEqual(self.coupon_in(self.payload_as(self.owner), coupon)["code"], "Group of 5+")

	def test_sums_the_discount_given_per_currency(self):
		coupon = self.create_coupon(discount_percentage=10)
		self.redeem(coupon)
		self.redeem(coupon)

		payload = self.payload_as(self.owner)

		self.assertEqual(payload["discounted"], [{"currency": "INR", "amount": 200}])

	def test_lists_ticket_types_with_prices(self):
		vip = str(
			EventTicketTypeFactory.create(
				event=self.event, title="VIP", prices=[{"currency": "USD", "price": 60}]
			).name
		)

		rows = {row["name"]: row for row in self.payload_as(self.owner)["ticket_types"]}

		self.assertEqual(rows[vip]["title"], "VIP")
		self.assertEqual(rows[vip]["prices"], [{"currency": "USD", "price": 60}])

	def test_viewer_reads_without_write(self):
		self.assertFalse(self.payload_as(self.viewer)["can_write"])
		self.assertTrue(self.payload_as(self.owner)["can_write"])

	def test_outsider_refused(self):
		with self.set_user(self.outsider), self.assertRaises(CannotManageEvent):
			get_event_coupons(self.event)
