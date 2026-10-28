import textwrap
from functools import cached_property

from frappe import _
from frappe.utils import get_url

from buzz.events.doctype.buzz_team.team_map import TeamMap
from buzz.events.doctype.buzz_team.team_page import EventTimeline, group_by_day
from buzz.www.event.meta import DESCRIPTION_LENGTH
from buzz.www.events import enabled_topics, events_with_topic, icon_url, topic_page_url


class TopicPage(EventTimeline):
	"""Context for a topic's public page: the event timeline, over the topic's events."""

	def __init__(self, topic):
		self.topic = topic

	def as_context(self) -> dict:
		upcoming = [self.card(event) for event in self.upcoming_events]
		past = [self.card(event) for event in self.past_events]
		return {
			"title": self.topic.name,
			"stats": self.stats(),
			"related_topics": self.related_topics(),
			"upcoming_days": group_by_day(upcoming),
			"past_days": group_by_day(past),
			"meta": self.meta(),
			**TeamMap(upcoming, past).as_context(),
		}

	@cached_property
	def topic_events(self) -> list[str]:
		return events_with_topic(self.topic.name) or [""]

	def event_filters(self) -> dict:
		return {"name": ["in", self.topic_events]}

	def stats(self) -> list[dict]:
		events = self.upcoming_events
		if not events:
			return []
		cities = len({event.city for event in events if event.city})
		hosts = len({event.host_name for event in events})
		return [
			{"value": len(events), "label": _("upcoming")},
			{"value": cities, "label": _("city") if cities == 1 else _("cities")},
			{"value": hosts, "label": _("host") if hosts == 1 else _("hosts")},
		]

	def related_topics(self) -> list[dict]:
		return [
			{"name": topic.name, "url": topic_page_url(topic), "icon_url": icon_url(topic.icon_svg)}
			for topic in enabled_topics()
			if topic.is_published and topic.name != self.topic.name
		]

	def meta(self) -> dict:
		text = self.topic.short_description or ""
		return {
			"url": get_url(f"/{self.topic.route}"),
			"description": textwrap.shorten(text, DESCRIPTION_LENGTH, placeholder="…") if text else "",
		}
