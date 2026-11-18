import frappe
from frappe.mcp.tools import success_result
from frappe.utils import add_days, today
from pydantic import ValidationError

from buzz.api.exceptions import NotPermitted
from buzz.mcp.registry import tools_for_user
from buzz.mcp.tools.attendee import ATTENDEE_TOOLS
from buzz.mcp.tools.organizer import ORGANIZER_TOOLS
from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import (
	BuzzEventCollaboratorFactory,
	BuzzEventFactory,
	EventBookingFactory,
	EventTicketFactory,
	TalkProposalFactory,
	UserFactory,
)

REFUSED_ERRORS = (frappe.PermissionError, frappe.DoesNotExistError, NotPermitted)

# The collaborator holds View on the event's details and guests, nothing else.
MATRIX = """
tool                            owner  collaborator  other_organizer  booker  stranger
get_event                       yes    yes           no               no      no
list_event_guests               yes    yes           no               no      no
get_guest                       yes    yes           no               no      no
get_registration_trend          yes    yes           no               no      no
list_ticket_types               yes    no            no               no      no
get_sales_summary               yes    no            no               no      no
list_event_proposals            yes    no            no               no      no
list_my_teams                   yes    yes           yes              yes     yes
get_team_overview               yes    no            no               no      no
list_my_events                  yes    yes           yes              yes     yes
list_my_bookings                yes    yes           yes              yes     yes
get_booking                     yes    yes           no               yes     no
get_ticket                      yes    yes           no               yes     no
list_my_proposals               yes    yes           yes              yes     yes
list_my_sponsorship_enquiries   yes    yes           yes              yes     yes
"""


def parse_matrix(table: str) -> dict[str, dict[str, bool]]:
	header, *rows = (line.split() for line in table.strip().splitlines())
	personas = header[1:]
	return {row[0]: dict(zip(personas, (cell == "yes" for cell in row[1:]), strict=True)) for row in rows}


def find_tool(name: str):
	return next(tool for tool in ATTENDEE_TOOLS + ORGANIZER_TOOLS if tool.name == name)


class McpToolTestCase(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.collaborator = BuzzEventCollaboratorFactory.create("accepted", event=cls.event_a).user
		cls.booker = UserFactory.create_once("mcp-booker@example.com").name
		cls.stranger = UserFactory.create_once("mcp-stranger@example.com").name
		cls.booking = EventBookingFactory.create(event=cls.event_a, user=cls.booker).name
		cls.ticket = EventTicketFactory.create(
			"submitted", event=cls.event_a, booking=cls.booking, attendee_email=cls.booker
		).name

	def call(self, user: str, name: str, **arguments):
		tool = find_tool(name)
		with self.set_user(user):
			validated = tool.arguments.model_validate(arguments)
			return success_result(tool.handler(**validated.model_dump()))["structuredContent"]


class TestPermissionMatrix(McpToolTestCase):
	def personas(self) -> dict[str, str]:
		return {
			"owner": self.alice,
			"collaborator": self.collaborator,
			"other_organizer": self.bob,
			"booker": self.booker,
			"stranger": self.stranger,
		}

	def arguments(self) -> dict[str, dict]:
		event = str(self.event_a)
		return {
			"get_event": {"event": event},
			"list_event_guests": {"event": event},
			"get_guest": {"event": event, "guest": self.ticket},
			"get_registration_trend": {"event": event},
			"list_ticket_types": {"event": event},
			"get_sales_summary": {"event": event},
			"list_event_proposals": {"event": event},
			"get_team_overview": {"team": self.team_a},
			"get_booking": {"booking_id": self.booking},
			"get_ticket": {"ticket_id": self.ticket},
		}

	def test_every_tool_has_a_row(self):
		tools = {tool.name for tool in ATTENDEE_TOOLS + ORGANIZER_TOOLS}
		self.assertEqual(set(parse_matrix(MATRIX)), tools)

	def test_matrix(self):
		personas = self.personas()
		arguments = self.arguments()
		for name, expected in parse_matrix(MATRIX).items():
			for persona, allowed in expected.items():
				with self.subTest(tool=name, persona=persona):
					self.assert_access(personas[persona], name, arguments.get(name, {}), allowed)

	def assert_access(self, user: str, name: str, arguments: dict, allowed: bool):
		if allowed:
			self.assertIsInstance(self.call(user, name, **arguments), dict)
			return
		with self.assertRaises(REFUSED_ERRORS):
			self.call(user, name, **arguments)


class TestToolPayloads(McpToolTestCase):
	def test_website_user_gets_only_attendee_tools(self):
		with self.set_user(self.booker):
			self.assertEqual(tools_for_user(), ATTENDEE_TOOLS)

	def test_team_member_gets_both_sets(self):
		with self.set_user(self.alice):
			self.assertEqual(tools_for_user(), ATTENDEE_TOOLS + ORGANIZER_TOOLS)

	def test_collaborator_gets_both_sets(self):
		with self.set_user(self.collaborator):
			self.assertEqual(tools_for_user(), ATTENDEE_TOOLS + ORGANIZER_TOOLS)

	def test_desk_user_gets_both_sets(self):
		with self.set_user("Administrator"):
			self.assertEqual(tools_for_user(), ATTENDEE_TOOLS + ORGANIZER_TOOLS)

	def test_guest_list_leaves_out_contact_details(self):
		page = self.call(self.alice, "list_event_guests", event=str(self.event_a))
		self.assertEqual([guest["name"] for guest in page["guests"]], [self.ticket])
		self.assertNotIn("attendee_email", page["guests"][0])

	def test_proposal_list_leaves_out_speaker_emails(self):
		TalkProposalFactory.create(
			event=self.event_a, speakers=[{"first_name": "Ada", "email": "ada@example.com"}]
		)
		page = self.call(self.alice, "list_event_proposals", event=str(self.event_a))
		self.assertEqual(page["proposals"][0]["speakers"], [{"first_name": "Ada", "last_name": None}])

	def test_my_events_are_paged(self):
		BuzzEventFactory.create_list(2, team=self.team_a, start_date=add_days(today(), 30))
		page = self.call(self.alice, "list_my_events", role="hosting", limit=1)
		self.assertEqual(len(page["events"]), 1)
		self.assertTrue(page["has_next_page"])

	def test_one_guest_includes_contact_details(self):
		guest = self.call(self.alice, "get_guest", event=str(self.event_a), guest=self.ticket)
		self.assertEqual(guest["attendee_email"], self.booker)

	def test_paged_tools_default_to_20_and_cap_at_50(self):
		paged = [
			tool for tool in ATTENDEE_TOOLS + ORGANIZER_TOOLS if "limit" in tool.input_schema["properties"]
		]
		self.assertEqual(
			{tool.name for tool in paged},
			{"list_event_guests", "list_event_proposals", "list_my_bookings", "list_my_events"},
		)
		for tool in paged:
			required = dict.fromkeys(tool.input_schema.get("required", []), "1")
			with self.subTest(tool=tool.name):
				self.assertEqual(tool.arguments.model_validate(required).limit, 20)
				with self.assertRaises(ValidationError):
					tool.arguments.model_validate(required | {"limit": 51})

	def test_my_bookings_lists_the_users_own(self):
		page = self.call(self.booker, "list_my_bookings")["result"]
		self.assertEqual([booking["name"] for booking in page["bookings"]], [self.booking])
		self.assertEqual(page["bookings"][0]["event"], str(self.event_a))
		self.assertFalse(page["has_next_page"])
		self.assertEqual(self.call(self.stranger, "list_my_bookings")["result"]["bookings"], [])

	def test_my_teams_lists_only_the_users_teams(self):
		teams = self.call(self.bob, "list_my_teams")["result"]
		self.assertNotIn(self.team_a, [team["name"] for team in teams])
