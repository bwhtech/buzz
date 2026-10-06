from contextlib import contextmanager
from unittest.mock import patch

import frappe


@contextmanager
def capturing():
	"""Telemetry on, and whatever was captured sent as if the transaction committed."""
	with (
		patch("buzz.telemetry.is_enabled", return_value=True),
		patch("buzz.telemetry.frappe_capture") as mock_capture,
	):
		yield mock_capture
		frappe.db.after_commit.run()


def captured(mock_capture) -> list[tuple[str, dict]]:
	return [(call.args[0], call.kwargs.get("properties", {})) for call in mock_capture.call_args_list]


def captured_names(mock_capture) -> list[str]:
	return [name for name, _properties in captured(mock_capture)]


def properties_of(mock_capture, event: str) -> dict:
	matches = [properties for name, properties in captured(mock_capture) if name == event]
	if len(matches) != 1:
		raise AssertionError(f"expected one {event}, got {captured_names(mock_capture)}")
	return matches[0]
