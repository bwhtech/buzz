import re
from html import escape

from bs4 import BeautifulSoup, NavigableString, Tag

LINE_BREAK = "\x00"
KEPT_INLINE_TAGS = {"b", "strong", "i", "em", "u", "a"}
INLINE_TAGS = KEPT_INLINE_TAGS | {"span", "font", "small", "big", "sup", "sub", "o:p", "label"}
DROPPED_TAGS = {"style", "script", "head", "title", "meta", "img", "picture", "svg", "hr"}


class HTMLLines:
	"""Flattens any HTML into lines of inline markup, so content from a rich text editor,
	an email client or a plain textarea is read the same way: one entry per visual line,
	with an empty entry wherever the source left a gap."""

	def __init__(self, html: str, text_newlines: bool = False):
		# A textarea's line breaks reach the page as raw newlines inside the text.
		self.text_newlines = text_newlines
		self.parts: list[str] = []
		self.walk(BeautifulSoup(html or "", "html.parser"))

	def lines(self) -> list[str]:
		return [clean_line(line) for line in "".join(self.parts).split(LINE_BREAK)]

	def paragraphs(self) -> list[list[str]]:
		"""Lines grouped by the blank lines between them."""
		groups: list[list[str]] = [[]]
		for line in self.lines():
			if line:
				groups[-1].append(line)
			elif groups[-1]:
				groups.append([])
		return [group for group in groups if group]

	def walk(self, node: Tag):
		for child in node.children:
			if isinstance(child, NavigableString):
				self.add_text(str(child), child)
			elif child.name == "br":
				self.parts.append(LINE_BREAK)
			elif child.name not in DROPPED_TAGS:
				self.add_element(child)

	def add_text(self, text: str, node: NavigableString):
		if type(node) is not NavigableString:  # comments, CDATA, doctype
			return
		text = escape(text, quote=False)
		self.parts.append(text.replace("\n", LINE_BREAK) if self.text_newlines else text)

	def add_element(self, element: Tag):
		if element.name in INLINE_TAGS:
			return self.add_inline(element)
		self.break_line()
		self.walk(element)
		self.break_line()

	def break_line(self):
		# Adjacent blocks are adjacent lines; only an empty block or a <br> leaves a gap.
		while self.parts and not self.parts[-1].strip(" \t\r\n"):
			self.parts.pop()
		if self.parts and self.parts[-1] != LINE_BREAK:
			self.parts.append(LINE_BREAK)

	def add_inline(self, element: Tag):
		kept = element.name in KEPT_INLINE_TAGS
		if kept:
			self.parts.append(opening_tag(element))
		self.walk(element)
		if kept:
			self.parts.append(f"</{element.name}>")


def opening_tag(element: Tag) -> str:
	href = element.get("href") if element.name == "a" else None
	if href and href.startswith(("http://", "https://", "mailto:")):
		return f'<a href="{escape(href)}" target="_blank" rel="noopener">'
	return f"<{element.name}>"


def clean_line(line: str) -> str:
	"""Collapses whitespace, and drops a line that is only markup or a dashed rule."""
	line = re.sub(r"[\s\u00a0]+", " ", line.replace("&nbsp;", " ")).strip()
	text = re.sub(r"<[^>]+>", "", line).strip()
	if not text or re.fullmatch(r"[-_=*~]{3,}", text):
		return ""
	# Reparsing closes inline tags a line break split across lines.
	return str(BeautifulSoup(line, "html.parser"))


def plain_text(html: str | None, separator: str = "") -> str:
	return BeautifulSoup(html or "", "html.parser").get_text(separator)
