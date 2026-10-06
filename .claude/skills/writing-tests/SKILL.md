---
name: writing-tests
description: How backend tests build their fixtures in Buzz — factories under buzz/tests/factories/ powered by frappe_factory_bot, instead of raw frappe.get_doc({...}).insert(). Covers authoring a factory, traits, overrides, the flags passthrough, and the Frappe-level traps (per-class rollback, prompt autoname, the User creation throttle, doc cache). Use this whenever writing or modifying a python test under buzz/, and when the user says "add a test", "write tests for X", "convert these tests", or "this test needs a fixture".
---

# Writing backend tests in Buzz

Fixtures come from factories in `buzz/tests/factories/`, built on `frappe_factory_bot`
(`apps/frappe_factory_bot`, repo `harshtandiya/frappe_factory_bot`). It is a bench-level dev
app: `.github/actions/setup-bench` runs `bench get-app` for it, and it is **not** in
`required_apps`, because production Buzz does not need it.

Faker comes with frappe. Do not add it to `pyproject.toml`.

## Rules

1. **Never** build a fixture with `frappe.get_doc({...}).insert()` or `frappe.new_doc(...)`.
   Use a factory. If the doctype has none, write it first.
2. One factory per doctype: `buzz/tests/factories/<package>/<snake_case_doctype>_factory.py`,
   where `<package>` is `core` (Frappe and payments doctypes), `events`, `ticketing` or
   `proposals`. Class `<PascalCaseDocType>Factory(BaseFactory[<DocClass>])`, re-exported from
   `buzz/tests/factories/__init__.py`; import it from `buzz.tests.factories`. The generic is
   the real controller class, so the result is typed. `buzz/tests/test_factories.py` creates
   every factory in `__all__`, so a new factory is smoke-tested once it is exported.
3. `default_attributes` sets only what `.insert()` needs. Leave out fields with a DocType
   default or a controller fallback (`Event Booking.status`, the INR 0 price row
   `Event Ticket Type.before_validate` adds).
4. **An override set used in a third test becomes a trait.** A trait names a configuration —
   `EventTicketTypeFactory.create("paid", event=event)` — so a doctype change is a one-line
   fix and the call site reads as the concept. Keep each trait to one idea; they compose.
   Used once or twice, it stays an override.
5. **Defaults that hit a unique constraint must be unique per call.** Rollback is per
   *class*, not per test. `_fake.unique.*` dedupes within one process only, so a value that
   is the **primary key** of a prompt-autonamed doctype uses `frappe.generate_hash(length=8)`
   — those rows outlive the run.
6. Foreign keys honour the override before creating anything:
   `self.overrides.get("event") or BuzzEventFactory.create().name`. Import the related
   factory *inside* the property, or the imports cycle.
7. **Do not override `create()`** — it breaks `create_list` / `build_list`. Add a named
   classmethod instead (`BuzzTeamFactory.create_owned_by`, `UserFactory.create_once`).
8. No `__del_override__`. Cleanup is the per-class rollback; a delete on garbage collection
   can remove a doc a downstream fixture still links to.
9. Child tables get no factory. Pass them as nested dicts on the parent.
10. **Assert what you set.** A value the test checks is passed explicitly —
    `TicketAddOnFactory.create(event=event, price=500)`, then `assertEqual(total, 500)`. Never
    assert against a value read back from the fixture (`self.add_on.price`): a changed default
    turns the assertion into a tautology.
11. **No fixed dates.** Use `add_days(today(), n)`; a hard-coded future date expires.

## Authoring a factory

Tabs, line length 110, as in `pyproject.toml`.

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
			"is_published": 1,
		}

	@property
	def paid(self) -> dict[str, Any]:
		return {"prices": [{"currency": "INR", "price": 500}]}
```

| Call | Returns | Saved? |
| --- | --- | --- |
| `Factory.build(*traits, **overrides)` | `T` | no |
| `Factory.create(*traits, **overrides)` | `T` | yes |
| `Factory.build_list(n, *traits, **overrides)` | `list[T]` | no |
| `Factory.create_list(n, *traits, **overrides)` | `list[T]` | yes |

Precedence: overrides > traits > defaults. An unknown trait raises `TypeError`.

Every `@property` defined on the factory class itself, except `default_attributes`, is a
trait. Traits are found in the class's own `__dict__`, so a trait inherited from a base
factory is rejected. A helper value goes in a method or a module constant, not a property.
Traits run after `self.overrides` is set, so they can honour an override like defaults do.

## The `flags` passthrough

`frappe.get_doc()` drops `flags` from the attribute dict (`RESERVED_KEYWORDS`), so
`BaseFactory.build` applies it separately. **Flags only arrive through overrides**, never
through `default_attributes` or a trait.

```python
EventTicketTypeFactory.create(event=event, flags={"ignore_permissions": True})
```

`insert()` keeps the flag unless the kwarg is passed, so `has_permission` short-circuits on
it. Administrator does not need it, and a test *about* permissions must not use it.

Controller flags travel the same way: `Buzz Team.flags.owner_user` sets an Owner other than
the session user.

## Traps

**Administrator must not own throwaway teams.** `setup_test_records()` gives Administrator
exactly one team, and Event Template and event proposal submissions fill `team` from a sole
membership. `process_booking` commits, so its fixtures survive rollback. A second
Administrator team leaks across runs and breaks that lookup. Use
`BuzzTeamFactory.create_owned_by()`.

**`Buzz Event` names are autoincrement integers.** `.name` is an `int` in memory, and the
whitelisted APIs type-check `event: str`. Pass `str(event.name)`, and compare against `str(...)`
when the other side came from the database.

**`get_fullname` caches per process.** A user rebuilt in a later class keeps the earlier
name in that cache. Set the name the test asserts, and read it from the field the code reads.

**`frappe.set_user` is allowed only in `test_*.py`.** The `frappe-setuser` semgrep rule
fails CI anywhere else, for example in `buzz/tests/base_test_cases.py` or a factory. Use
`with self.set_user(user):`, `self.enterContext(self.set_user(user))` in `setUp`, or
`frappe.tests.classes.context_managers.set_user` outside a test case.

**User creation is throttled** at 60 new users an hour (`User.throttle_user_creation`), and
test users leak. For a fixed identity use `UserFactory.create_once(email)`; use `create()`
only for a distinct user.

**Prompt-autonamed doctypes need `name` in the attributes** (`Event Category`), or
`_prompt_autoname` throws.

**`before_insert` / `validate` can clobber an override.** Set the field after `.create()` and
save again.

**`create()` swaps the doc's class** to a generated `TempSubclass` (for the `__del__` hook).
`isinstance` still holds, but `type(doc) is EventTicketType` is false and `pickle` fails.
Pass `doc.name`, not the doc, to `frappe.cache` or `frappe.enqueue`. `build()` does not swap.

**Rollback restores a Single but not its cached copy.** A fixture touching
`Buzz Team Settings` or `Buzz Settings` needs `frappe.clear_document_cache`.

## Consuming factories

```python
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import BuzzEventFactory, UserFactory


class BookingTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.booker = UserFactory.create_once("booking-owner@example.com").name
		cls.event = BuzzEventFactory.create()
```

`buzz/api/booking/test_booking.py` is the reference conversion.

Never import from another `test_*.py`. Shared base classes (`BookingTestCase`,
`CouponTestCase`, `BookingRefundTestCase`, `SponsorshipTestCase`, `TeamPermissionTestCase`)
live in `buzz/tests/base_test_cases.py`. Shared non-fixture helpers (email queue readers,
telemetry capture, `clear_map_link_cache`) live in `buzz/tests/utils.py`.

Use the Frappe context managers rather than manual cleanup: `self.set_user`,
`self.change_settings` (Singles only), `self.freeze_time`, `self.patch_hooks`.
`Buzz Team Settings` is not a Single, so use `BuzzTeamFactory.set_settings(team, values)`.

CI formats with ruff 0.8.1. Run `uvx ruff@0.8.1 format buzz && uvx ruff@0.8.1 check buzz`
before pushing; a newer ruff wraps lines differently.

## Running tests

```bash
bench --site buzz.localhost run-tests --module buzz.api.booking.test_booking
bench --site buzz.localhost run-tests --module buzz.api.booking.test_booking --test test_shape
```

`testbuzz.localhost` is the CI-parity site and reproduces failures `buzz.localhost` hides.
