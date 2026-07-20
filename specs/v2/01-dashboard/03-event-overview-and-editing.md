# 03 — Event overview & editing

| Phase | Depends on | Status |
|---|---|---|
| B | 01-dashboard/02 | Draft |

## Goal

The Overview tab becomes the event's home: KPI strip + editable core fields + publish control —
day-to-day event setup no longer needs Desk.

## Demo criteria (definition of done)

Manager edits title, dates, venue, and banner from Overview; the public event page reflects it.
KPI numbers match Desk counts. Publish/unpublish from the header works.

## Scope

### In
- KPI strip (bookings, tickets sold, gross revenue, check-ins)
- Editable core `Buzz Event` fields + banner upload + publish/unpublish + danger zone
### Out (deferred to)
- Sponsor/email/tax/gateway settings → step 12; schedule → step 10; featured speakers → Phase E

## Backend changes

`buzz/api/events.py` (new module):

```python
@frappe.whitelist()
def get_event_stats(event: str) -> dict:
    """{bookings, tickets_sold, gross_revenue, currency, checked_in}
    Aggregates via frappe.qb (Count/Sum) over Event Booking (docstatus 1),
    Event Ticket, Event Payment (payment_received=1), Event Check In.
    Permission: frappe.has_permission("Buzz Event", "read", event) explicit check.
    """
```

## Frontend changes

- `OverviewTab.vue` (replaces stub):
  - KPI strip — dashboard archetype: 4 stats in a `divide-x divide-outline-gray-2` row, values
    `text-2xl font-semibold tabular-nums`, labels `text-sm text-ink-gray-5`; `useCall` to
    `get_event_stats`.
  - Details form — `useDoc("Buzz Event", eventId)` bound `FormControl`s: `title`,
    `short_description`, `about` (`Editor` from `frappe-ui/editor`), `start_date`/`end_date` +
    `start_time`/`end_time`, `time_zone` (Combobox), `medium` Select, `venue` (Link → Event Venue,
    team-scoped by hooks), `category`, `host` (Link → Event Host), `route` (slug input with
    prefix hint), `banner_image` + `card_image` + `meta_image` via `FileUploader`.
    Save via `doc.save.submit()` on a sticky footer `Button` (dirty-state aware).
  - Header publish control: `is_published` toggle `Button` (solid green "Publish" / subtle
    "Unpublish") with `dialog.confirm` when unpublishing an event with sold tickets.
  - Danger zone card: cancel event (writes status; framework delete stays Desk-only).
- `data/events.ts`: add `useEventDoc(eventId)` + `useEventStats(eventId)`.

## API contract

| Endpoint | Method | Params | Returns | Auth |
|---|---|---|---|---|
| `buzz.api.events.get_event_stats` | GET | `event` | `{bookings, tickets_sold, gross_revenue, currency, checked_in}` | read perm on event (team member) |

## Permissions notes

Viewer: form read-only (disable inputs by `team_role`), stats visible. Write path enforced
server-side by team hooks.

## Demo script

1. Overview shows KPIs; cross-check numbers in Desk report views.
2. Change title + upload banner → save → public event page shows both.
3. Unpublish → public page 404s/hides; publish again.
4. Viewer-role member sees stats + disabled form.

## Acceptance criteria (merge gate)

### Automated tests — `buzz/tests/test_event_stats.py` (new)
`bench --site buzz.localhost run-tests --module buzz.tests.test_event_stats`
- Fixture: event with 2 bookings (one paid, one pending), 3 tickets, 1 check-in →
  `get_event_stats` returns exact counts; gross revenue sums only `payment_received=1`.
- Zero-activity event → all zeros, no division/None errors.
- Cross-team caller → `PermissionError`.

### Browser checks (agent-browser, dev server :8080)
1. Overview tab → KPI strip values match the fixture counts.
2. Edit title + upload banner → save → public event page shows new title + banner image request
   200.
3. Unpublish (event with sold tickets) → confirm dialog appears → public page hides/404s the
   event; publish again → restored.
4. Viewer-role member → form inputs disabled, KPIs visible, save button absent.
5. Dirty-state: edit a field, navigate tabs → unsaved-changes guard (or explicit sticky save
   still shows dirty state).

## Dependencies & risks

- Revenue definition: sum of `Event Payment.amount` where `payment_received=1` — document the
  formula in the endpoint docstring; taxes make "gross" ambiguous (note for spec 12).
