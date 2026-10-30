# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

from frappe.tests import IntegrationTestCase

from buzz.tests.factories import BuzzEventFactory, EventTalkFactory


class IntegrationTestEventTalk(IntegrationTestCase):
	def test_an_event_can_have_several_talks_without_proposals(self):
		event = BuzzEventFactory.create().name
		EventTalkFactory.create(event=event)
		self.assertTrue(EventTalkFactory.create(event=event).name)
