import re

from buzz.html_lines import HTMLLines, plain_text

BULLET = re.compile(r"^(?:[-*•\u2013]|\d{1,2}[.)])\s+")
INLINE_NUMBERS = re.compile(r"(?:^|\s)(\d{1,2})[.)]\s+")
INLINE_BULLETS = re.compile(r"\s+[•▪●]\s+")
LABEL = re.compile(r"^[^.?!]{2,60}:$")
MARKDOWN_BOLD = re.compile(r"\*\*(.+?)\*\*")
STRUCTURE = re.compile(r"<(ul|ol|h[1-6]|table|blockquote)[\s>]", re.IGNORECASE)
SENTENCE = re.compile(r"[^.?!]+[.?!]+(?:\s+|$)|[^.?!]+$")
LONG_PARAGRAPH = 480
PARAGRAPH_TARGET = 280


class DescriptionFormatter:
	"""Gives a submitted description readable structure without changing its words:
	paragraphs from the speaker's line breaks, lists from bullets or inline numbering, and
	walls of text split at sentence ends."""

	def __init__(self, html: str):
		self.original = html or ""
		self.paragraphs = HTMLLines(self.original, text_newlines=True).paragraphs()

	def html(self) -> str:
		if is_structured(self.original):
			return self.original
		return "".join(block for lines in self.paragraphs for block in self.blocks(lines))

	def blocks(self, lines: list[str]) -> list[str]:
		if len(lines) > 1 and all(BULLET.match(plain_text(line)) for line in lines[1:]):
			return [*self.blocks(lines[:1]), as_list([BULLET.sub("", line) for line in lines[1:]])]
		if len(lines) > 1:
			return [block for line in lines for block in self.blocks([line])]
		return self.line_blocks(MARKDOWN_BOLD.sub(r"<strong>\1</strong>", lines[0]))

	def line_blocks(self, line: str) -> list[str]:
		lead, items, numbered = split_items(line)
		if items:
			return [*self.lead_blocks(lead), as_list(items, numbered)]
		if LABEL.match(plain_text(line)):
			return [f"<h4>{line.rstrip(':')}</h4>"]
		return [f"<p>{chunk}</p>" for chunk in sentence_chunks(line)]

	def lead_blocks(self, lead: str) -> list[str]:
		"""A lead ending in "…with:" introduces the list, so its last sentence is the heading."""
		sentences = SENTENCE.findall(lead)
		if not sentences or not lead.endswith(":"):
			return self.line_blocks(lead) if lead else []
		rest = "".join(sentences[:-1]).strip()
		return [*(self.line_blocks(rest) if rest else []), f"<h4>{sentences[-1].strip().rstrip(':')}</h4>"]


def is_structured(html: str) -> bool:
	"""A description already laid out in an editor is shown as written."""
	return bool(STRUCTURE.search(html)) or len(re.findall(r"<p[\s>]", html)) >= 3


def split_items(line: str) -> tuple[str, list[str], bool]:
	"""Splits "lead: 1. one 2. two" or "lead • one • two" into its lead and items."""
	numbers = list(INLINE_NUMBERS.finditer(line))
	if len(numbers) >= 2 and [int(m.group(1)) for m in numbers] == list(range(1, len(numbers) + 1)):
		bounds = [m.start() for m in numbers] + [len(line)]
		items = [line[m.end() : bounds[i + 1]].strip() for i, m in enumerate(numbers)]
		return line[: numbers[0].start()].strip(), items, True
	pieces = INLINE_BULLETS.split(line)
	if len(pieces) >= 3:
		return pieces[0].strip(), [piece.strip() for piece in pieces[1:]], False
	return "", [], False


def sentence_chunks(line: str) -> list[str]:
	if len(plain_text(line)) <= LONG_PARAGRAPH or "<" in line:
		return [line]
	chunks, current = [], ""
	for sentence in SENTENCE.findall(line):
		current += sentence
		if len(current) >= PARAGRAPH_TARGET:
			chunks.append(current.strip())
			current = ""
	return [*chunks, current.strip()] if current.strip() else chunks


def as_list(items: list[str], numbered: bool = False) -> str:
	tag = "ol" if numbered else "ul"
	return f"<{tag}>" + "".join(f"<li>{item}</li>" for item in items) + f"</{tag}>"
