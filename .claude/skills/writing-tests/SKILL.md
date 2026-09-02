---
name: writing-tests
description: How backend tests build their fixtures in Buzz — factories under buzz/tests/factories/ powered by frappe_factory_bot, instead of raw frappe.get_doc({...}).insert(). Covers authoring a factory, traits, overrides, the flags passthrough, and the Frappe-level traps (per-class rollback, prompt autoname, the User creation throttle, doc cache). Use this whenever writing or modifying a python test under buzz/, and when the user says "add a test", "write tests for X", "convert these tests", or "this test needs a fixture".
---

# Writing backend tests in Buzz

Fixtures come from factories in `buzz/tests/factories/`, built on `frappe_factory_bot`
(`apps/frappe_factory_bot`, repo `harshtandiya/frappe_factory_bot`). It is a bench-level
dev app — installed by `bench get-app` in `.github/actions/setup-bench`, deliberately
**not** in `required_apps`, because production Buzz does not need it.

Faker comes free: frappe depends on it, so `from faker import Faker` works. Do not add it
to `pyproject.toml`.

## Rules

1. **Never** `frappe.get_doc({...}).insert()` or `frappe.new_doc(...)` to build a fixture.
   Use a factory. If the doctype has none, write it first.
2. One factory per doctype, `buzz/tests/factories/<snake_case_doctype>_factory.py`, class
   `<PascalCaseDocType>Factory(BaseFactory[<DocClass>])`. Parameterise the generic with the
   real controller class so the IDE types the result. Re-export from `__init__.py`.
3. `default_attributes` sets only what `.insert()` actually needs. Fields with a DocType
   default (`Event Ticket Type.currency` is `INR`, `Event Booking.status` is
   `Approval Pending`) stay out.
4. **When the same override set turns up in a third test, promote it to a trait.** Overrides
   are for one-offs; a trait is for a configuration that has a name — "a paid ticket type",
   "a closed event", "a submitted booking". Promoting it puts those field values in one
   place, so a doctype change is a one-line fix instead of a grep, and the call site starts
   reading as the concept instead of as a bag of fields:
   `EventTicketTypeFactory.create("paid", event=event)` says what the test needs, where
   `create(price=500, event=event)` repeated six times makes the reader work it out every
   time. Traits compose, so keep each to a single idea and apply several rather than
   building one combined trait. Don't run ahead of the evidence, though — a configuration
   used once is an override, and inventing traits before anything repeats just moves the
   noise into the factory.
5. **Every default that hits a unique constraint must be unique per call.** Rollback is per
   *class*, not per test, and three test files already comment on it
   (`test_buzz_team.py:27`, `:155`, `test_buzz_event.py:165`) — a fixed default collides
   with the previous test in the same class. `_fake.unique.*` covers that, but it only
   dedupes within one process: for a value that is the doctype's **primary key** (anything
   prompt-autonamed) use `frappe.generate_hash(length=8)`, because those rows outlive the
   run that made them and Faker will eventually repeat itself.
6. Foreign keys honour the override before creating anything:
   `self.overrides.get("event") or BuzzEventFactory.create().name`. Without this, passing
   `event=<existing>` still spawns an orphan event. Import the related factory *inside* the
   property, not at module top, or the imports cycle.
7. **Do not override `create()`.** It breaks `create_list` / `build_list`. A doctype needing
   more than an insert gets a separate factory for the dependency, referenced from
   `default_attributes` — or a small named classmethod alongside `create()`
   (`BuzzTeamFactory.create_owned_by`, `UserFactory.create_once`).
8. No `__del_override__`. The base default is a no-op, cleanup is the per-class rollback,
   and overriding it means the doc can be garbage-collected — and deleted — while a
   downstream fixture still holds its name.
9. Child tables (`Event Booking Attendee`, `Additional Field`, …) get no factory. They go in
   as nested dicts on the parent's attributes.

## Authoring a factory

Tabs, line length 110 — match `pyproject.toml`, not another app's style.

```python
from typing import Any

from faker import Faker
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory

from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import EventTicketType

_fake = Faker()


class EventTicketTypeFactory(BaseFactory[EventTicketType]):
	doctype = "Event Ticket Type"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories.buzz_event_factory import BuzzEventFactory

		return {
			"event": self.overrides.get("event") or BuzzEventFactory.create().name,
			"title": f"Ticket {_fake.unique.word().capitalize()}",
			"price": 0,
			"is_published": 1,
		}

	@property
	def paid(self) -> dict[str, Any]:
		return {"price": 500}
```

| Call | Returns | Saved? |
| --- | --- | --- |
| `Factory.build(*traits, **overrides)` | `T` | no |
| `Factory.create(*traits, **overrides)` | `T` | yes |
| `Factory.build_list(n, *traits, **overrides)` | `list[T]` | no |
| `Factory.create_list(n, *traits, **overrides)` | `list[T]` | yes |

Precedence: overrides > traits > defaults. An unknown trait raises `TypeError`.

## The `flags` passthrough

`flags` is in Frappe's `RESERVED_KEYWORDS`, so `frappe.get_doc()` drops it from the
attribute dict. `BaseFactory.build` therefore applies it separately — which means **flags
only arrive through overrides, never through `default_attributes` or a trait**.

```python
EventTicketTypeFactory.create(event=event, flags={"ignore_permissions": True})
```

`insert()` leaves `flags.ignore_permissions` alone unless the kwarg is passed
(`frappe/model/document.py:709`), so the flag survives and `has_permission` short-circuits
on it. Use it where the old code passed `ignore_permissions=True`; a test running as
Administrator does not need it, and a test that is *about* permissions should not use it.

The same route carries doctype flags the controller reads itself —
`Buzz Team.flags.owner_user` is how a team gets an Owner other than the session user.

## Traps

**Administrator must not own throwaway teams.** `create_default_team_for` picks the *first*
enabled Owner membership (`buzz_team.py:19`), and test rows are not always rolled back —
`process_booking` commits, so its fixtures survive. A team inserted plainly as Administrator
therefore becomes Administrator's "default team" for every later run on that site, and
`setup_test_records()` then fails with `Venue Test Venue belongs to another team.` Use
`BuzzTeamFactory.create_owned_by()`.

**User creation is throttled.** `User.throttle_user_creation` throws `Throttled` past 60 new
users an hour (`throttle_user_limit`). Test users leak, so a suite that mints a fresh user
per fixture trips it after a couple of runs. Where the identity is fixed and one record is
all you want, use `UserFactory.create_once(email)`; use `create()` only when the test needs
a genuinely distinct user.

**Prompt-autonamed doctypes need `name` in the attributes.** `Event Category` and
`Event Host` use `autoname: prompt`, and `_prompt_autoname` throws when `doc.name` is unset
(`frappe/model/naming.py:225`). Set `"name"` in `default_attributes`.

**`before_insert` / `validate` can clobber an override.** Overrides are merged into the dict
that becomes the doc, and those hooks run after. Set the field after `.create()` and save
again.

**The rollback restores a Single but not its cached copy** (`test_buzz_team_settings.py:47`).
A fixture touching `Buzz Team Settings` or `Buzz Settings` needs
`frappe.clear_document_cache`.

## Consuming factories

```python
import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import BuzzEventFactory, EventTicketTypeFactory, UserFactory


class BookingTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.booker = UserFactory.create_once("booking-owner@example.com").name
		cls.event = BuzzEventFactory.create(flags={"ignore_permissions": True})
```

`buzz/api/booking/test_booking.py` is the reference conversion.

Some older test modules still export ad-hoc helpers — `create_user` / `create_owned_team` /
`payload_for` in `test_buzz_team.py`, `ensure_prompt_named_record` in `test_forms.py`,
`create_event` / `create_ticket` in `test_permissions.py`. They are being retired module by
module; `context_local.md` tracks who still imports what. Do not add new callers.

## Running tests

```bash
bench --site buzz.localhost run-tests --app buzz
bench --site buzz.localhost run-tests --module buzz.api.booking.test_booking
bench --site buzz.localhost run-tests --module buzz.api.booking.test_booking --test test_shape
```

Redis must be up (`bench start`, or `redis-server config/redis_cache.conf --daemonize yes`
and the same for `redis_queue.conf`) — without it global search sync asserts and every test
errors out. `testbuzz.localhost` is the CI-parity site and reproduces failures
`buzz.localhost` hides.
