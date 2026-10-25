import re
from html import escape

from bs4 import BeautifulSoup, Tag

from buzz.html_lines import HTMLLines, plain_text

# Where each mail client puts the message being replied to.
QUOTE_SELECTORS = ", ".join(
	[
		".gmail_quote",
		"blockquote[type=cite]",
		".yahoo_quoted",
		".moz-cite-prefix",
		"#divRplyFwdMsg",
		"#appendonsend",
		".zmail_extra",
		"div[style*='border-top:solid #E1E1E1']",  # Outlook desktop
		"div[style*='border-top:solid #B5C4DF']",  # older Outlook
	]
)
SIGNATURE_SELECTORS = ".gmail_signature, .gmail_signature_prefix, .moz-signature, #Signature"
# "From:" alone is Outlook's bold label; with text after it, an address must follow.
QUOTE_HEADER = re.compile(r"^(On .{4,200} wrote:|-+ ?Original Message ?-+|From:( .*@.*)?)$", re.IGNORECASE)
PLAIN_QUOTE_HEADER = re.compile(
	r"^(On [^\n]{4,200}\n?[^\n]{0,100}wrote:|-+ ?Original Message ?-+|From: .+\n(Sent|Date): |>)",
	re.IGNORECASE | re.MULTILINE,
)
# A tag name ends at a space, a slash or ">", which an address such as <b@x.com> never does.
HTML_TAG = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*[\s/>]")
SIGN_OFF = re.compile(
	r"^((many |warm |kind |best )?(thanks|regards)( (&|and) regards)?|best|cheers|sincerely|"
	r"thank you|warmly)[,.!]?$",
	re.IGNORECASE,
)
DEVICE_SIGNATURE = re.compile(r"^(sent from my .+|get outlook for .+)$", re.IGNORECASE)
NAME_LINE_LIMIT = 40
SNIPPET_LENGTH = 200
# Stands in for an image while lines are cut, so what survives tells which images were in the body.
IMAGE_MARKER = re.compile(r"\x01(\d+)\x01")


class EmailContent:
	"""An email reduced to what was written in it: the quoted thread, signature, images and
	client styling are taken out, leaving short paragraphs in the dashboard's own type."""

	def __init__(self, html: str):
		# A text/plain email is stored as is, and its line breaks are its only structure.
		self.plain = not HTML_TAG.search(html or "")
		if self.plain:
			html, self.quoted = split_plain_quote(html or "")
		self.soup = BeautifulSoup(html or "", "html.parser")
		if not self.plain:
			self.quoted = self.extract_quote()
		for node in self.soup.select(SIGNATURE_SELECTORS):
			node.decompose()
		self.image_sources = self.mark_images()
		self.paragraphs = signed_off(HTMLLines(str(self.soup), self.plain).paragraphs())

	def body(self) -> str:
		return to_html(without_markers(self.paragraphs))

	def snippet(self) -> str:
		return " ".join(plain_text(re.sub(r"</p>|<br>", " ", self.body())).split())[:SNIPPET_LENGTH]

	def body_image_sources(self) -> list[str]:
		"""Images placed in what was written, as opposed to the signature or the quote."""
		lines = "".join(line for paragraph in self.paragraphs for line in paragraph)
		return [self.image_sources[int(index)] for index in IMAGE_MARKER.findall(lines)]

	def mark_images(self) -> list[str]:
		sources = []
		for image in self.soup.find_all("img"):
			image.replace_with(f"\x01{len(sources)}\x01")
			sources.append(image.get("src") or "")
		return sources

	def quoted_body(self) -> str:
		return to_html(HTMLLines(self.quoted, self.plain).paragraphs()) if self.quoted else ""

	def extract_quote(self) -> str:
		start = self.soup.select_one(QUOTE_SELECTORS) or self.quote_header()
		if not start:
			return ""
		quoted = [start, *following(start)]
		html = "".join(str(node) for node in quoted)
		for node in quoted:
			node.extract()
		return html

	def quote_header(self) -> Tag | None:
		texts = self.soup.find_all(string=QUOTE_HEADER)
		return next((text.parent for text in texts if text.parent.get_text(strip=True) == text.strip()), None)


def split_plain_quote(text: str) -> tuple[str, str]:
	"""The written part and the quoted thread of a text/plain email, both escaped for HTML."""
	header = PLAIN_QUOTE_HEADER.search(text)
	cut = header.start() if header else len(text)
	return escape(text[:cut], quote=False), escape(text[cut:], quote=False)


def following(node) -> list:
	"""Everything after `node` in reading order, outside `node` itself."""
	nodes = []
	while node is not None and node.parent is not None:
		nodes.extend(node.next_siblings)
		node = node.parent
	return nodes


def signed_off(paragraphs: list[list[str]]) -> list[list[str]]:
	"""Keeps the sign-off and the name under it, and drops the signature block below."""
	lines = [(index, line) for index, paragraph in enumerate(paragraphs) for line in paragraph]
	for position, (index, line) in enumerate(lines):
		text = plain_text(line).strip()
		if DEVICE_SIGNATURE.match(text):
			return trimmed(paragraphs, lines[:position])
		if SIGN_OFF.match(text):
			name = next((entry for entry in lines[position + 1 :] if line_text(entry[1])), None)
			# A sentence after "Thanks!" means the message goes on; a sign-off is followed by a name.
			if name and not is_name(line_text(name[1])):
				continue
			# Images beside the name are the signature's, not the message's.
			keep = [(index, line)] + ([(name[0], IMAGE_MARKER.sub("", name[1]))] if name else [])
			return trimmed(paragraphs, lines[:position] + keep)
	return paragraphs


def is_name(text: str) -> bool:
	return len(text) <= NAME_LINE_LIMIT and not text.endswith((".", "?", "!"))


def line_text(line: str) -> str:
	return IMAGE_MARKER.sub("", plain_text(line)).strip()


def trimmed(paragraphs: list[list[str]], kept: list[tuple[int, str]]) -> list[list[str]]:
	result: dict[int, list[str]] = {}
	for index, line in kept:
		result.setdefault(index, []).append(line)
	return list(result.values())


def without_markers(paragraphs: list[list[str]]) -> list[list[str]]:
	stripped = (
		[kept for line in paragraph if (kept := IMAGE_MARKER.sub("", line).strip())]
		for paragraph in paragraphs
	)
	return [paragraph for paragraph in stripped if paragraph]


def to_html(paragraphs: list[list[str]]) -> str:
	return "".join(f"<p>{'<br>'.join(lines)}</p>" for lines in paragraphs)
