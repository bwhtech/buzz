# 05 — Buzz Team Settings

| Phase | Depends on | Status |
|---|---|---|
| Foundation | 00-teams/01–03 | Draft |

## Goal

Split tenant-specific configuration out of the site-wide `Buzz Settings` Single into a per-team
**`Buzz Team Settings`** doctype (regular doctype, one row per team — not a Single, since it is
per tenant). `Buzz Settings` remains for truly global, admin-level, backend-only config.

## Demo criteria (definition of done)

Two teams set different ticket-transfer windows; each team's events enforce their own window in
the attendee flow (`can_transfer_ticket`). `bench migrate` seeds every existing team's settings
from current global values — attendee-visible behavior unchanged on upgrade day.

## Scope

### In
- `Buzz Team Settings` doctype + auto-create on team creation + seed patch
- Resolution helpers + rewiring existing read sites (audit table below)
- API for the frontend settings dialog
### Out (deferred to)
- Settings UI → `01-dashboard/13` (Team Settings dialog gets a "Defaults" section)
- Per-event overrides of these values (event-level fields already exist for some, e.g.
  `ticket_email_template` on Buzz Event — that hierarchy stays: event field → team settings)

## Field split decision

### Moves to `Buzz Team Settings` (per team)

| fieldname | type | today read at |
|---|---|---|
| `allow_transfer_ticket_before_event_start_days` | Int | `buzz/api/__init__.py:151` (`can_transfer_ticket`) |
| `allow_add_ons_change_before_event_start_days` | Int | `buzz/api/__init__.py:166` (`can_change_add_ons`) |
| `allow_ticket_cancellation_request_before_event_start_days` | Int | `buzz/api/__init__.py:191` (`can_request_cancellation`) |
| `support_email` | Data | ticket emails / public pages |
| `default_ticket_email_template` | Link Email Template | `event_ticket.py:106` |
| `auto_send_pitch_deck` | Check | `sponsorship_enquiry.py:82` |
| `default_sponsor_deck_email_template` | Link Email Template | `sponsorship_enquiry.py:82` |
| `default_sponsor_deck_reply_to` | Data | same |
| `default_sponsor_deck_cc` | Small Text | same |
| `default_webinar_template` | Link | `buzz_event.py:198` (verify field exists in Buzz Settings JSON — read in code, missing from schema dump; reconcile while implementing) |

### Stays in `Buzz Settings` (site-wide, Desk/System Manager only)

| fieldname | why global |
|---|---|
| `login_banner` | site login page (`auth.py:13`) |
| `accept_event_proposals`, `allow_guest_event_proposals`, `event_proposal_banner_title`, `event_proposal_success_title`, `event_proposal_success_message` | inbound event-proposal funnel is site-level (pre-team) — `forms.py:367` |
| `custom_fields_go_after_this` | form-layout plumbing |

## Backend changes

### New doctype: `Buzz Team Settings` (module: Events)

- `team` Link → Buzz Team, reqd, **unique** — one settings row per team.
- All "moves" fields above.
- `autoname: field:team` (row addressable as the team name).
- Not a child table, not a Single — plain doctype so permission hooks from `00-teams/03` apply
  (add it to the tenant inventory: query condition = its own `team` column; write requires
  Owner/Admin — settings are team administration, stricter than Manager).

### Lifecycle

- `Buzz Team.after_insert` → `buzz.teams.create_team_settings(team)` seeding field values from
  current `Buzz Settings` globals (copy-on-create; **no runtime fallback chain** — one read,
  predictable; changing a global later never silently mutates existing teams).
- Patch `buzz/patches/create_team_settings_for_existing_teams.py`: idempotent seed for teams
  created before this step.

### Resolution helpers — `buzz/teams.py`

```python
def get_team_settings(team: str) -> Document:
    """frappe.get_cached_doc('Buzz Team Settings', team); creates+seeds if missing (self-heal)."""

def get_event_team_settings(event: str) -> Document:
    """Resolve event -> team -> settings. The standard entry point for attendee-flow code."""
```

### Rewire call sites (audit — the heart of this step)

| Site | Change |
|---|---|
| `buzz/api/__init__.py:151,166,191` | `frappe.get_single("Buzz Settings")` → `get_event_team_settings(event)` (event in scope at each site) |
| `buzz/ticketing/doctype/event_ticket/event_ticket.py:106` | event-level `ticket_email_template` stays first; fallback → team settings default |
| `buzz/proposals/doctype/sponsorship_enquiry/sponsorship_enquiry.py:82` | sponsor-deck defaults → team settings (enquiry → event → team) |
| `buzz/events/doctype/buzz_event/buzz_event.py:198` | webinar template default → team settings |
| `buzz/api/auth.py:13`, `buzz/api/forms.py:367` | unchanged (global) |

Add regression tests: per-team window enforcement + upgrade parity (seeded values equal old
globals).

## Frontend changes

None here. `01-dashboard/13` Team Settings dialog gains a **Defaults** section (windows, support
email, email-template Links, sponsor-deck defaults) bound to `useDoc("Buzz Team Settings", team)`.
Owner/Admin editable, others read-only.

## API contract

No bespoke endpoints — `useDoc` CRUD under permission hooks suffices (row addressable by team
name via `autoname: field:team`).

## Permissions notes

- Read: any team member (attendee-flow reads happen server-side, unaffected).
- Write: Owner/Admin only (stricter than the Manager write default — add a doctype-specific
  branch in `buzz/permissions.py:team_has_permission` or a dedicated `has_permission` mapping).
- `Buzz Settings` keeps System-Manager-only Desk access; never surfaced in the dashboard.

## Demo script

1. `bench migrate` → every team has a seeded `Buzz Team Settings` row; values match old globals.
2. Team A sets transfer window 7 days; Team B leaves 2.
3. Attendee with ticket to A's event (5 days out) → transfer blocked; B's event (5 days out) →
   allowed.
4. New team created via onboarding → settings row exists immediately.
5. As Manager-role member: `useDoc` save on team settings → server denies.

## Acceptance criteria (merge gate)

### Automated tests — `buzz/tests/test_team_settings.py` (new)
`bench --site buzz.localhost run-tests --module buzz.tests.test_team_settings`
- Creating a `Buzz Team` auto-creates its `Buzz Team Settings` row seeded from `Buzz Settings`
  values (assert field-by-field for the moved set).
- `get_team_settings` self-heals a missing row.
- Window enforcement: team A window 7 days, team B 2 days → `can_transfer_ticket` /
  `can_change_add_ons` / `can_request_cancellation` return opposite verdicts for tickets on
  events 5 days out.
- Ticket email template resolution order: event field → team settings default (both branches).
- Sponsor-deck defaults resolved from the enquiry's event's team.
- Write perms: Manager-role member save raises; Owner/Admin save succeeds; cross-team read
  excluded (list isolation).
- Seed patch idempotent; seeded values equal pre-migration globals (upgrade-parity case).

### Browser checks (agent-browser)
1. Attendee with a ticket to team A's event 5 days out (window 7) → ticket detail page: transfer
   action absent/disabled; same-aged ticket on team B's event (window 2) → transfer action
   available.

## Dependencies & risks

- **Decision recorded: copy-on-create, no fallback chain.** Trade-off: platform admin changing a
  global default doesn't propagate to existing teams. Revisit only if that becomes a real need.
- `default_webinar_template` schema/code mismatch (read in `buzz_event.py:198`, absent from the
  current Buzz Settings field dump) — reconcile during implementation.
- Update `00-teams/00-plan.md` tenant inventory + `01-dashboard/13` scope when this lands (done in
  this spec's PR).
