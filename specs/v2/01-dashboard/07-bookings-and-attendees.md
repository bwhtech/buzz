# 07 — Bookings & attendees

| Phase | Depends on | Status |
|---|---|---|
| C | 01-dashboard/03 | Draft |

## Goal

See the money and the people: Bookings tab (payments, offline confirmation) and Attendees tab
(search, filter, export).

## Demo criteria (definition of done)

A test booking completed publicly appears in the Bookings tab; manager confirms an offline
payment; finds an attendee by name in Attendees and exports CSV.

## Scope

### In
- Bookings tab: list + detail panel + confirm-offline-payment action
- Attendees tab: merged ticket/attendee list, search, filters, CSV export
### Out (deferred to)
- Refunds (needs future payments pillar); cancellation-request approval queue → Phase E
- Manual check-in from attendee rows → step 08

## Backend changes

`buzz/api/bookings.py` (new):

```python
@frappe.whitelist()
def confirm_offline_payment(booking: str) -> dict:
    """Marks the booking's Event Payment as received + submits booking
    (mirrors current Desk flow on Event Payment / Event Booking).
    Guard: write perm on the booking (team Manager+)."""

@frappe.whitelist()
def export_attendees(event: str) -> str:
    """CSV string of attendees (name, email, ticket type, add-ons, checked-in, booking id).
    Built with frappe.get_all joins — one query, no N+1. Read perm on event."""
```

## Frontend changes

- `src/pages/manage/event/BookingsTab.vue` — `List`: booking id, booker (name/email), amount
  (`tabular-nums`), payment status `Badge` (Paid green / Pending orange / Failed red), gateway or
  "Offline", created (`relative time`). Filter `Select` by payment status. Row → detail panel
  (right slide-over `Dialog`): attendees, `Event Payment` info (gateway, id, amount, tax),
  applied coupon, action `Button` "Mark payment received" (offline, unpaid only;
  `dialog.confirm`).
- `src/pages/manage/event/AttendeesTab.vue` — `List` over `Event Ticket` joined attendee fields:
  name, email, ticket type, add-ons summary, checked-in `Badge`. Debounced search `FormControl`
  (name/email), filters: ticket type `Select`, checked-in `Select`. Header: count summary +
  "Export CSV" `Button` → `export_attendees` → client download.
- `data/bookings.ts`, `data/attendees.ts`.

## API contract

| Endpoint | Method | Params | Returns | Auth |
|---|---|---|---|---|
| `buzz.api.bookings.confirm_offline_payment` | POST | `booking` | `{ok, payment_status}` | team Manager+ |
| `buzz.api.bookings.export_attendees` | GET | `event` | CSV text | team member (read) |

## Permissions notes

Bookings/tickets query conditions include the owner carve-out (00-teams/03) — manager lists here
are filtered by `event`, so only team data shows. Viewer read-only (no confirm button).

## Demo script

1. Complete a public test booking (offline method) → Bookings tab shows Pending.
2. "Mark payment received" → confirm → Badge flips Paid; attendee gets ticket email.
3. Attendees tab → search attendee name → row found; filter by ticket type.
4. Export CSV → opens with correct columns/rows.

## Acceptance criteria (merge gate)

### Automated tests — `buzz/tests/test_bookings_api.py` (new)
`bench --site buzz.localhost run-tests --module buzz.tests.test_bookings_api`
- `confirm_offline_payment`: pending offline booking → payment marked received, booking
  submitted, ticket emails queued; already-paid booking raises; gateway (non-offline) booking
  raises; Viewer-role caller raises `PermissionError`.
- `export_attendees`: CSV header + row count match fixture; add-ons column aggregates values;
  cross-team caller raises; query count bounded (no N+1 — assert with `frappe.db` query counter
  or `assertNumQueries`-style helper).

### Browser checks (agent-browser, dev server :8080)
1. Fresh session → offline-method booking on the event → Bookings tab (manager session) shows
   Pending badge.
2. Row → detail panel → "Mark payment received" → confirm → badge flips Paid without reload.
3. Attendees tab → search by attendee name → row filtered; filter by ticket type works.
4. "Export CSV" → file downloads; parse: header columns as specced, row for the new attendee.
5. Viewer-role member → no "Mark payment received" button; tabs render read-only.

## Dependencies & risks

- `confirm_offline_payment` must reuse the existing `mark_payment_as_received`/submit logic from
  `buzz/payments.py` + booking controller — no duplicate state machine.
- Realtime: `useList` auto-refresh via socket (`refetch_resource` pattern) is a nice-to-have;
  manual refresh button is the fallback.
