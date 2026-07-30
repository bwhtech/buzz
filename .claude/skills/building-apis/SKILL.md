---
name: building-apis
description: How whitelisted HTTP APIs are built in this app — the buzz/api/<domain>/ package layout, pydantic APIRequest/APIResponse schemas, BuzzAPIError subclasses, service classes, and the frappe.whitelist conventions (type annotations, methods=["POST"], allow_guest + nosemgrep). Use this whenever writing a new endpoint under buzz/api/ — with its response payload, error classes, service class and tests — and also when the user says "add an API", "new endpoint", "whitelisted method", "expose X to the dashboard", or "the dashboard needs data for X".
---

# Building APIs in Buzz

Every dashboard call lands on a `@frappe.whitelist()` function under `buzz/api/`. The URL
*is* the dotted module path (`buzz.api.tickets.get_ticket_details`), so the file layout is the
public API surface — that's why it's organised by domain and why endpoint names never change
casually.

Every domain under `buzz/api/` follows the shape below. New work matches it; code that
doesn't predates the convention and is not the pattern to copy.

## Package layout

One package per domain, each file with one job:

```
buzz/api/<domain>/
  __init__.py      endpoints only — decorate, delegate, return
  services.py      the work: service class and/or module functions
  schemas.py       pydantic request/response models
  exceptions.py    named error classes
  test_<domain>.py IntegrationTestCase tests
```

Split further when a file passes ~300 lines — `buzz/api/booking/` has `guests.py`,
`coupons.py`, `details.py`, `event_data.py`. A domain thin enough that a service layer
would be an empty hop (`payments`, `auth`) gets no `services.py`; don't add one for
symmetry.

## The endpoint

Endpoints are one to three lines. They validate by annotation, delegate, and return:

```python
@frappe.whitelist()
def get_ticket_details(ticket_id: str) -> TicketDetailsResponse:
	return services.TicketService(ticket_id).details()
```

Rules that are load-bearing, not style:

- **Annotate every argument.** `require_type_annotated_api_methods = True` in `hooks.py`
  makes frappe reject unannotated whitelisted args at runtime, and CI's semgrep
  `missing-argument-type-hint` fails the build. Annotate the return type too — with a
  response model it doubles as the payload contract.
- **Anything that writes takes `methods=["POST"]`.** frappe skips CSRF validation outside
  `UNSAFE_HTTP_METHODS` and only auto-commits on POST/PUT, so a write reachable over GET is
  both unprotected and silently rolled back. Leave reads unrestricted — pinning their verb
  only risks a caller.
- **`allow_guest=True` needs the nosemgrep comment**, on its own line above the decorator
  when the decorator is doing more than one thing:

```python
# nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="identifier", limit=5, seconds=3600)
def send_guest_booking_otp(event: int, identifier: str) -> dict | None:
	return guests.send_booking_otp(event, identifier)
```

- **Permission checks belong in the service, not the endpoint** — in the one function every
  caller routes through. `get_booking_details` shipped with no check at all because the
  guard sat in a sibling endpoint rather than in the shared builder.
- **Don't whitelist internals.** Lifecycle hooks (`after_insert`) become remotely
  re-runnable through `run_doc_method`, and service functions like
  `get_payment_link_for_booking` let a client name its own amount source. If nothing calls
  it over HTTP, it isn't an endpoint.

## Schemas

`buzz/api/schemas.py` holds the two bases. Requests extend `APIRequest`
(`extra="ignore"`, whitespace stripped), responses extend `APIResponse` (`extra="forbid"`).

```python
class TicketAddOnDetail(APIResponse):
	id: str
	title: str | None
	price: float | None
	options: list[str]
```

The response model replaces hand-built dicts, so the wire shape is the type signature.
Two things to know:

- **`APIResponse.__json__` returns raw field values on purpose** and deep-converts only
  nested `APIResponse` models. It does not call `model_dump()`: `frappe._dict.__getattr__`
  is `dict.get`, so pydantic mistakes an untyped row for a model carrying a `None`
  serializer and raises `"'None' is not an instance of SchemaSerializer"`. Documents and
  query rows are left to frappe's `json_handler`, as before.
- **Whole documents and meta-shaped rows stay `Any` / `list`**, with a one-line comment
  saying why. Typing them would reshape the payload the dashboard already reads. Rows from
  a fixed `get_all` field list, on the other hand, get a real model.

A pydantic model *as a parameter* reshapes the wire payload — the client has to nest its
body under the parameter name (`{"booking": {...}}`). Worth it for something like
`process_booking`, which otherwise takes 16 flat arguments; not worth it for two. Dynamic
keys defined per event stay `list[dict]`: link values arrive as ints, and typing them makes
frappe's arg validation reject the payload.

When a payload changes shape, the dashboard's `createResource` transform changes with it in
the same commit. Grep `dashboard/src` for the endpoint path.

## Errors

`buzz/api/exceptions.py` has the base and three status-carrying subclasses:
`BuzzAPIError` (400), `ResourceNotFound` (404), `NotPermitted` (403), `Conflict` (409).
Each domain's `exceptions.py` subclasses those and declares its own copy:

```python
class TransferWindowClosed(Conflict):
	title = _lt("Transfers Closed")
	message = _lt("The transfer window for this event has closed.")
```

```python
TransferWindowClosed.throw()
TicketNotInBooking.throw(ticket_id=ticket_id, booking_id=booking_id)  # message.format(**context)
```

- **`_lt`, not `_`** — class bodies run at import, before a request has a language. The
  translation extractor already scans `_lt`.
- **`throw()`, never `raise SomeError`.** `throw()` routes through `frappe.throw` so the
  text reaches `_server_messages`, which is what the dashboard renders as
  `err.messages[0]`. A bare raise skips msgprint and leaves the user staring at "Internal
  Server Error". There's a test in `test_exceptions.py` keeping that distinction visible.
- **A class per condition the user can hit differently**, not one per throw site. Four
  named errors for booking, not fourteen; generic internal failures keep a plain
  `frappe.throw`.
- **Leave frappe's own errors alone** when they already carry the right status and a clear
  message — `DoesNotExistError` on an unknown record, `AuthenticationError` for login.
  Wrap one only when the dashboard branches on `exc_type` (as `LoginRequired` does), and
  then move both sides in the same commit.
- Site misconfiguration (a missing app) stays 4xx: a 5xx writes an Error Log on every click.

## Services

Reach for a class when there's per-request state — usually one document. The id goes in the
constructor along with the cheap guards; the document is a plain property:

```python
class CheckinService:
	"""Front-desk check-in for a single ticket. Restricted to Frontdesk Manager."""

	def __init__(self, ticket_id: str):
		frappe.only_for("Frontdesk Manager", True)
		if not frappe.db.exists("Event Ticket", ticket_id):
			TicketNotFound.throw()
		self.ticket_id = ticket_id

	@property
	def ticket(self) -> "EventTicket":
		return frappe.get_cached_doc("Event Ticket", self.ticket_id)
```

- **Plain property, not `cached_property`.** `get_cached_doc` already caches; a second
  layer only adds one that can go stale inside a request.
- **Import doctype controllers under `TYPE_CHECKING`** for those return annotations — no
  runtime import, so no import cycle through controllers that import from `buzz.api`.
- **List queries and cross-doctype operations stay module functions.** A class with a
  single method is ceremony.
- Keep methods near ten lines; a long `process()` reads as a sequence of named steps
  (`validate_event`, `build_booking`, `finalize`).
- Batch per-row lookups into maps instead of a `get_value` per row. Buzz Event autonames to
  integers while Link fields arrive as strings, so map keys need an explicit `str()` — the
  SQL those lookups replaced was coercing silently.
- `frappe.parse_json`, not `json.loads` — it already returns a `frappe._dict` for dicts.
- A manual `frappe.db.commit()` needs
  `# nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit` and a reason.

## Tests

`test_<domain>.py` in the domain package, `IntegrationTestCase`, importing the endpoints
(not the services) so the whitelisted surface is what's covered. Assert on the error
classes: `with self.assertRaises(TransferWindowClosed)`.

```bash
bench --site <site> run-tests --module buzz.api.tickets.test_tickets
```

Two traps that cost real debugging time:

- **Own your fixtures.** `IntegrationTestCase` rolls the database back but not the document
  cache. A test that mutates a shared record leaves the cache holding a value the rollback
  has since removed from the row — visible to every later test module in the same process.
  Create your own event rather than editing the shared one.
- **Singles can't be owned**, so drop them from the cache instead:
  `self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")`.
- `frappe.clear_messages()` in `setUp` if you assert on `frappe.local.message_log`.

Cover the payload key set when a response shape matters, and add a Playwright spec in
`e2e/` when the behaviour is one only a browser can catch — a client-side role gate, an
`exc_type` branch, keys a component renders.
