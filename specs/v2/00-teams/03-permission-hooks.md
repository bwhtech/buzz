# 03 — Permission hooks (row-level isolation)

| Phase | Depends on | Status |
|---|---|---|
| Foundation | 00-teams/02 | Draft |

## Goal

Team isolation actually enforced: a member of Team A can never list or open Team B's records —
in Desk, `frappe.client`, REST, and frappe-ui `useList` alike. Replaces the commented-out stubs at
`buzz/hooks.py:161-167`.

## Demo criteria (definition of done)

Two managers in two teams: Desk/API list views show only their own team's events and bookings;
direct URL to the other team's doc → 403. Simultaneously, a Guest completes a booking on a
published event and an attendee still sees their own booking at `/dashboard/account/bookings` —
zero regression.

## Scope

### In
- `buzz/permissions.py` with query-condition + has_permission implementations
- `hooks.py` wiring for every tenant doctype + `Buzz Team`/`Buzz Team Membership`
- Guest/attendee endpoint audit + regression test suite

### Out (deferred to)
- UI 403 page → `01-dashboard/01`
- Frontdesk check-in scoping niceties → `01-dashboard/08`

## Backend changes

### `buzz/permissions.py` (new, Gameplan pattern — one central module)

```python
TEAM_SCOPED_WRITE_ROLES = {"Owner", "Admin", "Manager"}
TEAM_SCOPED_DELETE_ROLES = {"Owner", "Admin"}

def team_query_conditions(user=None, doctype=None, **kwargs) -> str | None:
    """permission_query_conditions hook, shared by all tenant doctypes.

    Called by db_query as fn(user, doctype=doctype). Returns namespaced SQL:
    `tab{doctype}`.`team` in (select `team` from `tabBuzz Team Membership`
                              where `user` = %(user)s and `status` = 'Active')
    Built with frappe.qb / pypika criterion (framework renders + escapes it).
    System Manager / Administrator -> None (unrestricted).
    """

def membership_query_conditions(user=None, **kwargs) -> str | None:
    """For Buzz Team Membership itself: rows of teams the user belongs to."""

def team_doc_query_conditions(user=None, **kwargs) -> str | None:
    """For Buzz Team: teams the user is an Active member of."""

def team_has_permission(doc, ptype="read", user=None, **kwargs) -> bool:
    """has_permission hook — DENY-ONLY (composes over role perms).

    read/select/print/email/export/report -> any Active membership on doc.team
    write/create/submit/cancel/amend      -> team_role in TEAM_SCOPED_WRITE_ROLES
    delete                                -> team_role in TEAM_SCOPED_DELETE_ROLES
    System Manager -> True. doc.team unset -> True (pre-backfill tolerance).
    """
```

Notes:
- Signatures follow framework calling conventions verified in
  `frappe/model/db_query.py:get_permission_query_conditions` (`fn(user, doctype=...)`) and
  `frappe/permissions.py:has_controller_permissions` (`fn(doc=, ptype=, user=, debug=)`);
  `**kwargs` absorbs extras.
- One generic implementation, not per-doctype copies. Membership subquery built once via
  `frappe.qb` and rendered with `with_namespace=True`.
- **Attendee carve-out**: for `Event Booking`, `Event Ticket`, `Event Payment`,
  `Ticket Cancellation Request` the query condition is
  `(<team membership subquery> OR owner = user)` — attendees list *their own* docs today via
  framework `owner`/`if_owner` perms and existing API checks; team scoping must widen, not narrow,
  that access.

### `hooks.py` wiring

```python
permission_query_conditions = {
    "Buzz Team": "buzz.permissions.team_doc_query_conditions",
    "Buzz Team Membership": "buzz.permissions.membership_query_conditions",
    "Buzz Event": "buzz.permissions.team_query_conditions",
    # ... every doctype in the 00-plan.md tenant inventory
}
has_permission = {
    "Buzz Team": "buzz.permissions.team_doc_has_permission",
    "Buzz Event": "buzz.permissions.team_has_permission",
    # ... same inventory
}
```

### Guest & attendee flow audit (hard requirement of this step)

Every whitelisted endpoint in `buzz/api/__init__.py` is enumerated in the PR description with its
verdict. The critical ones:

| Endpoint | Path today | Verdict |
|---|---|---|
| `get_event_booking_data`, `validate_coupon` | guest-allowed reads of published event config | reads use `frappe.get_all` with explicit filters — must switch to `ignore_permissions=True` reads of *published* events only (guest has no membership) |
| `process_booking` | creates booking/attendees as guest or user | doc inserts already run with explicit flows; inserts get `ignore_permissions=True` where the actor is a non-member by design |
| `get_booking_details`, `get_ticket_details` | owner-checked | keep explicit owner checks; owner carve-out in query conditions keeps list views working |
| `transfer_ticket`, `change_add_on_preference`, `create_cancellation_request` | owner + window checks | unchanged; inserts stamped with team via cascade |
| `validate_ticket_for_checkin`, `checkin_ticket` | `frappe.only_for("Frontdesk Manager")` | additionally verify frontdesk user has Active membership (any role with check-in capability) in the ticket's team |

### Tests — `buzz/tests/test_team_permissions.py` (new)

1. Cross-team isolation: `frappe.get_list("Buzz Event")` as member A excludes team B's events;
   `frappe.get_doc(...).check_permission("read")` raises for B's event.
2. Role matrix: Viewer can read, cannot write; Manager can write, cannot delete; Admin can delete.
3. Guest booking end-to-end on a published event (existing test helpers) still passes.
4. Attendee reads own booking/tickets without membership.
5. Frontdesk of team A cannot check in team B's ticket.

## Frontend changes

None.

## API contract

No new endpoints.

## Permissions notes

This step **is** the permission layer — matrix in `00-teams/00-plan.md`. `has_permission` hooks can
only deny, never grant; base doctype role perms (`Event Manager` etc.) still gate capability.

## Demo script

1. Create teams A (alice) and B (bob), one event each.
2. As alice in Desk: Buzz Event list shows only A's event; open B's event URL → 403.
3. As alice via REST: `/api/resource/Buzz Event` → only A's.
4. Incognito guest: book a free ticket on B's published event → success; ticket email received.
5. Attendee logs in → `/dashboard/account/bookings` shows the booking.
6. `bench --site buzz.localhost run-tests --module buzz.tests.test_team_permissions` → green.

## Acceptance criteria (merge gate)

### Automated tests — `buzz/tests/test_team_permissions.py` (the suite defined above, expanded)
`bench --site buzz.localhost run-tests --module buzz.tests.test_team_permissions`
- Cross-team isolation: `frappe.get_list` excludes other team's rows for **every** doctype in the
  tenant inventory (parametrized); `check_permission("read")` raises cross-team.
- Role matrix: Viewer read-only; Manager write-not-delete; Admin delete; System Manager
  unrestricted.
- Owner carve-out: attendee (non-member) lists own `Event Booking`/`Event Ticket` rows.
- Frontdesk of team A cannot `checkin_ticket` for team B's ticket.
- NULL-team tolerance: doc with unset team readable by System Manager only; no exception raised.
- Guest API surface: `get_event_booking_data`, `validate_coupon`, `process_booking` (free ticket)
  succeed as Guest on a published event with hooks active.

### Browser checks (agent-browser)
1. Fresh session (no login) → open `/dashboard/book-tickets/<team-B-event-route>` → complete a
   free-ticket guest booking (OTP flow) → success screen; ticket email queued.
2. Log in as that attendee → `/dashboard/account/bookings` → booking visible; open ticket detail.
3. Log in as team-A manager → open Desk `/app/buzz-event` → assert list shows only team A's
   events; navigate to team B's event URL → 403/permission error page.

## Dependencies & risks

- **Highest-risk step in v2.** The attendee/guest carve-outs are the sharp edge — the test suite is
  a merge blocker, not optional.
- NULL `team` tolerance (`doc.team unset -> True` in has_permission; query condition still filters
  NULL out for non-System-Managers) keeps a half-migrated site from hard-breaking.
- Performance: membership subquery per list query; Frappe's role check stays Redis-cached. If it
  shows up in profiles, cache team IDs per user in `frappe.cache` keyed on membership modification.
