# 08 — Check-in desk

| Phase | Depends on | Status |
|---|---|---|
| C | 01-dashboard/07 | Draft |

## Goal

Check-in surfaced in the event workspace with live stats and manual check-in; Frontdesk-role
members get a focused, check-in-only experience.

## Demo criteria (definition of done)

Scan (or paste) a ticket → checked in, stats tick up, recent-check-ins feed updates. Manual
check-in from an attendee row works. A `Frontdesk`-role member logs in and sees only the check-in
surface.

## Scope

### In
- Check-in tab: stats, embedded scanner, recent check-ins feed, manual check-in
- Frontdesk-role navigation trimming
### Out (deferred to)
- Ticket-tear animation / confetti delight pass → future "check-in redesign" pillar
- Multi-day/date-wise check-in config UI → Phase E

## Backend changes

`buzz/api/events.py` addition:

```python
@frappe.whitelist()
def get_checkin_stats(event: str) -> dict:
    """{total_tickets, checked_in, by_ticket_type: [{ticket_type, total, checked_in}]}"""
```

`checkin_ticket` / `validate_ticket_for_checkin` (existing) gain the team-membership guard from
`00-teams/03` — no signature change.

## Frontend changes

- `src/pages/manage/event/CheckInTab.vue`:
  - Stats strip: checked-in/total overall + per ticket type (progress bars,
    `bg-surface-gray-2` track / `bg-surface-gray-7` fill).
  - Embedded scanner: reuse `CheckInScanner.vue` internals (html5-qrcode + existing
    `validate_ticket_for_checkin` → `checkin_ticket` flow) refactored into a
    `components/checkin/ScannerPanel.vue` shared by both surfaces.
  - Recent check-ins feed: last 20 `Event Check In` rows (attendee, ticket type, time), socket or
    poll refresh.
  - Manual check-in: search attendee (reuses Attendees data) → `Button` "Check in" per row.
- Attendees tab (step 07): row action "Check in" appears for roles with check-in capability.
- Frontdesk navigation: `ManagerLayout` reads `team_role`; `Frontdesk` sees sidebar with Events →
  event list rows deep-link straight to `/manage/events/:id/check-in`; other tabs hidden.
- Existing standalone `/check-in/:eventName` route kept (redirects to the workspace tab when the
  user has team access).

## API contract

| Endpoint | Method | Params | Returns | Auth |
|---|---|---|---|---|
| `buzz.api.events.get_checkin_stats` | GET | `event` | stats dict | team member w/ check-in capability |

## Permissions notes

Check-in capability: Owner/Admin/Manager/Frontdesk (matrix in `00-teams/00-plan.md`). Global
`Frontdesk Manager` Frappe role still required by the existing endpoints — granted automatically
by membership role sync.

## Demo script

1. Open Check-in tab → stats show 0/N.
2. Paste a valid ticket id in scanner input → success state, stats 1/N, feed shows the entry.
3. Duplicate scan → "already checked in" warning state.
4. Manual check-in from attendee search → works.
5. Log in as frontdesk-role user → sidebar trimmed; can check in; cannot open Tickets tab.

## Acceptance criteria (merge gate)

### Automated tests — `buzz/tests/test_checkin.py` (new or extend existing check-in tests)
`bench --site buzz.localhost run-tests --module buzz.tests.test_checkin`
- `get_checkin_stats`: fixture with 3 tickets / 1 checked-in → totals + per-ticket-type breakdown
  exact; cross-team caller raises.
- `checkin_ticket` team guard: frontdesk member of team A checking team B's ticket raises;
  same-team succeeds; duplicate check-in returns the already-checked-in response (existing
  behavior preserved).

### Browser checks (agent-browser, dev server :8080)
1. Check-in tab → stats strip shows 0/N; paste valid ticket ID in manual input → success state,
   stats tick to 1/N, feed shows the entry.
2. Same ticket again → "already checked in" warning state (no double record).
3. Attendees tab → row "Check in" action → works, stats update.
4. Frontdesk-role member logs in → sidebar shows only Events; event row deep-links to the
   check-in tab; Tickets tab route → blocked/hidden.
5. Standalone `/dashboard/check-in/<event>` still functions (regression for mid-event usage).

## Dependencies & risks

- Camera permissions on mobile — scanner panel must degrade to manual input (already does today).
- Refactor of `CheckInScanner.vue` must not regress the standalone route mid-event; feature-flag
  the redirect.
