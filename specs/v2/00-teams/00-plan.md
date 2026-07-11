# 00-teams — Plan

Multi-tenancy foundation. Everything in `01-dashboard/` assumes these steps have landed.

## Steps

| # | Step | Delivers |
|---|---|---|
| [01](01-team-doctypes-and-core-api.md) | Team doctypes & core API | `Buzz Team`, `Buzz Team Membership`, create/list/switch APIs, role fixtures, default team on install |
| [02](02-team-field-on-events-and-backfill.md) | Tenant field & backfill | `team` on `Buzz Event` + cascade to descendants, backfill patch |
| [03](03-permission-hooks.md) | Permission hooks | `buzz/permissions.py`, row-level isolation, guest-flow regression tests |
| [04](04-team-invitations.md) | Team invitations | User Invitation `after_accept` → membership creation |
| [05](05-team-settings.md) | Buzz Team Settings | per-team settings doctype split from site-wide `Buzz Settings`, seeded on create |

Order is strict: 01 → 02 → 03 → 04 → 05. Steps 01–03 unblock the dashboard tracer bullet
(`01-dashboard/01`); steps 04–05 unblock the members/invites/settings UI (`01-dashboard/13`).

## Design decisions (from earlier PRD research)

- **Standalone junction doctype** (`Buzz Team Membership`), not a child table à la Gameplan's
  `GP Member` — a user belongs to many teams and we query memberships by user constantly.
- **`team_role` is a Select enum** (`Owner/Admin/Manager/Frontdesk/Viewer`), not per-team Frappe
  Role records. Frappe global roles stay as *capability* gates (`Event Manager`, `Frontdesk
  Manager`, `Buzz User`); `team_role` gates *which team's data* and *what within it*.
- **Permission model = Gameplan pattern**: central `buzz/permissions.py` with
  `permission_query_conditions` (row-level list scoping via membership subquery) +
  deny-only `has_permission` hooks. Verified against
  `frappe/model/db_query.py:get_permission_query_conditions` and
  `frappe/permissions.py:has_controller_permissions` calling conventions.
- **Invitations reuse Frappe's `User Invitation`** (`frappe/core/doctype/user_invitation/`) via the
  `user_invitation` hook's `extra_invite_params` + `after_accept` — already partially declared in
  `buzz/hooks.py`.

## Tenant doctype inventory

**Team-direct** (user picks/creates under a team): `Buzz Event`, `Event Venue`, `Event Host`,
`Event Template`, `Buzz Campaign`.

**Derived-from-event** (`team` stamped from linked `event`): `Event Ticket Type`, `Ticket Add-on`,
`Buzz Coupon Code`, `Sponsorship Tier`, `Event Sponsor`, `Event Booking`, `Event Ticket`,
`Event Payment`, `Event Check In`, `Sponsorship Enquiry`, `Talk Proposal`, `Event Talk`,
`Event Track`, `Event Feedback`, `Additional Event Page`, `Offline Payment Method`,
`Ticket Cancellation Request`, `Buzz Custom Field`.

**Team-scoped, own `team` column**: `Buzz Team Settings` (one row per team, see
[05](05-team-settings.md); write restricted to Owner/Admin).

**Not team-scoped**: `Event Category` (global taxonomy), `Speaker Profile` (attendee-owned;
remodel pending — `../02-speaker-remodel.md`), `Event User Preferences` (per-user),
`Buzz Settings` (site-wide Single, global admin config only), `Event Proposal` (inbound, pre-team).

## Team role capability matrix

| Capability | Owner | Admin | Manager | Frontdesk | Viewer |
|---|---|---|---|---|---|
| Read team data | ✅ | ✅ | ✅ | check-in scope | ✅ |
| Create/edit events & children | ✅ | ✅ | ✅ | ❌ | ❌ |
| Delete records | ✅ | ✅ | ❌ | ❌ | ❌ |
| Check-in operations | ✅ | ✅ | ✅ | ✅ | ❌ |
| Manage members & invites | ✅ | ✅ | ❌ | ❌ | ❌ |
| Edit team profile / delete team | ✅ | ❌ | ❌ | ❌ | ❌ |

Mapping to Frappe global roles (granted automatically on membership save):
`Owner/Admin/Manager` → `Event Manager`; `Frontdesk` → `Frontdesk Manager`; all → `Buzz User`.
