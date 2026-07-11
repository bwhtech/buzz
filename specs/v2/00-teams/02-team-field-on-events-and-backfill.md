# 02 — Tenant field on events & backfill

| Phase | Depends on | Status |
|---|---|---|
| Foundation | 00-teams/01 | Draft |

## Goal

Every `Buzz Event` belongs to a team, and `team` is denormalized onto all event descendants so the
permission layer (step 03) is a single-column filter on every doctype.

## Demo criteria (definition of done)

`bench migrate` on a site with existing data leaves every `Buzz Event` and descendant row with
`team` set; creating an `Event Ticket Type` in Desk auto-stamps `team` from its event; creating a
`Buzz Event` without `team` fails validation.

## Scope

### In
- `team` field on all tenant doctypes (inventory in `00-plan.md`)
- Cascade helper + `doc_events` wiring
- Backfill patch

### Out (deferred to)
- Enforcement (hooks) → `03-permission-hooks.md`
- Per-team settings split of `Buzz Settings` → future (site-wide Single stays global for now)

## Backend changes

### Field additions

- **`Buzz Event`**: `team` Link → Buzz Team, **reqd**, `in_standard_filter`, indexed
  (`search_index: 1`). Placed in the first section next to `title`.
- **Team-direct doctypes** (`Event Venue`, `Event Host`, `Event Template`, `Buzz Campaign`):
  `team` Link → Buzz Team, reqd, indexed.
- **Derived-from-event doctypes** (all 18 in `00-plan.md` inventory): `team` Link → Buzz Team,
  read-only, hidden, indexed. Stamped, never user-entered.

### Cascade helper — `buzz/teams.py`

```python
def inherit_team_from_event(doc, method=None):
    """doc_events handler: stamp doc.team from its linked event."""
```

- Resolves the event link field (`event` on most doctypes) → `frappe.db.get_value("Buzz Event",
  event, "team")` and sets `doc.team`. Throws if the event has no team.
- Wired in `hooks.py` `doc_events` `before_insert` for every derived doctype. `validate` also
  re-stamps when the `event` link changed (ticket transfers between events don't exist, but coupon
  `event` is editable).
- Child tables (`Schedule Item`, `Buzz Event Form`, etc.) need **no** team field — they are
  reachable only through their parent and inherit its permissions.

### `Buzz Event` controller

`validate`: `team` required (schema-level reqd covers Desk; keep an explicit check for
`ignore_mandatory` code paths). New-event creation from the dashboard always passes the active team.

### Backfill patch — `buzz/patches/assign_default_team.py` (register in `patches.txt` after `create_default_teams`)

1. Site-default team: reuse the default team of the site's first System Manager/Event Manager
   (created by step 01's patch); create one (`"Default Team"`) if none exists.
2. `UPDATE tabBuzz Event SET team = <default> WHERE IFNULL(team, '') = ''` via
   `frappe.db.set_value`-style bulk (`frappe.qb.update` — no raw SQL).
3. Cascade to each derived doctype with a query-builder update joining on its `event` column.
4. Idempotent; safe to re-run.

> Decision recorded: **one site-default team** for backfill (not per-`Event Host` teams). Existing
> installs are single-tenant in practice; owners can reassign later from Desk.

## Frontend changes

None.

## API contract

No new endpoints.

## Permissions notes

None enforced yet — `team` is inert data until step 03. Ship 02 and 03 in quick succession; a site
sitting on 02 alone behaves exactly as today.

## Demo script

1. `bench --site buzz.localhost migrate`.
2. In Desk, open any pre-existing `Buzz Event` → `team` populated with the default team.
3. `frappe.db.count("Event Booking", {"team": ("is", "not set")})` → 0 (repeat per derived doctype).
4. Create a new `Event Ticket Type` for that event in Desk → `team` auto-stamped, read-only.
5. Try inserting a `Buzz Event` without `team` in console → `frappe.MandatoryError`.

## Acceptance criteria (merge gate)

### Automated tests — `buzz/tests/test_team_cascade.py` (new)
`bench --site buzz.localhost run-tests --module buzz.tests.test_team_cascade`
- Inserting `Event Ticket Type` / `Event Booking` / `Event Sponsor` for an event stamps `team`
  from the event (one parametrized case per derived doctype in the inventory).
- Changing a coupon's `event` link re-stamps `team` on validate.
- Inserting `Buzz Event` without `team` raises `MandatoryError` (both Desk path and
  `ignore_mandatory` guard).
- Backfill patch: seed legacy rows with NULL team → run patch → zero NULL-team rows across every
  doctype in the inventory; run patch again → no change (idempotent).

### Browser checks (agent-browser)
None — no UI in this step.

## Dependencies & risks

- Patch ordering: must run **after** doctype sync and step 01's `create_default_teams`
  (patches.txt order), and **before** step 03's hooks are exercised — NULL `team` under active
  hooks hides rows from everyone but System Manager.
- `bench migrate` required after schema change (per project convention).
