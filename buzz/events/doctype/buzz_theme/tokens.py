import re

from frappe import _

REQUIRED_TOKENS = {
	"page-bg": "Color",
	"surface": "Color",
	"surface-raised": "Color",
	"border": "Color",
	"ink": "Color",
	"ink-title": "Color",
	"ink-strong": "Color",
	"ink-body": "Color",
	"ink-muted": "Color",
	"accent": "Color",
	"accent-hover": "Color",
	"accent-ink": "Color",
	"font-body": "Font",
	"font-display": "Font",
	"radius": "Dimension",
	"radius-banner": "Dimension",
	"measure": "Dimension",
	"aside": "Dimension",
	"page-width": "Dimension",
}

# Fonts are picked by name, never typed: a free-text stack is a way out of the CSS rule.
FONT_STACKS = {
	"Inter": "InterVar, Inter, system-ui, sans-serif",
	"Newsreader": "Newsreader, Georgia, serif",
	"System": "system-ui, sans-serif",
	"Georgia": "Georgia, serif",
	"Monospace": "ui-monospace, monospace",
}

TOKEN_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
VALUE_PATTERNS = {
	"Color": re.compile(
		r"^(#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})|(rgba?|oklch)\([0-9.%,/ ]+\))$", re.IGNORECASE
	),
	"Dimension": re.compile(r"^(0|[0-9]*\.?[0-9]+(px|rem|em|ch|%))$"),
}


def token_error(token: str, token_type: str, value: str) -> str | None:
	if not TOKEN_NAME.match(token or ""):
		return _("Token {0} may only use lowercase letters, digits and hyphens").format(token)
	expected_type = REQUIRED_TOKENS.get(token)
	if expected_type and token_type != expected_type:
		return _("Token {0} must be of type {1}").format(token, expected_type)
	if not is_valid_value(token_type, value or ""):
		return _("{0} is not a valid {1} for token {2}").format(value, token_type, token)
	return None


def is_valid_value(token_type: str, value: str) -> bool:
	if token_type == "Font":
		return value in FONT_STACKS
	pattern = VALUE_PATTERNS.get(token_type)
	return bool(pattern and pattern.match(value))


def css_value(token_type: str, value: str) -> str:
	return FONT_STACKS[value] if token_type == "Font" else value
