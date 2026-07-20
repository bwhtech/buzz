# 01 — Team doctypes & core API

| Phase | Depends on | Status |
|---|---|---|
| Foundation | — | Draft |

## Goal

Introduce the tenancy primitives — `Buzz Team` and `Buzz Team Membership` — plus the minimal API
the dashboard shell will consume (my teams, active team, create team). Includes the missing role
fixtures and default-team creation for existing installs.

## Demo criteria (definition of done)

Two fresh users each create a team via the API; `get_my_teams` returns only their own team with
`team_role: Owner`; `set_active_team` persists across requests; saving a membership auto-grants the
mapped Frappe role.

## Scope

### In
- `Buzz Team`, `Buzz Team Membership` doctypes + controllers
- `buzz/teams.py` domain module, `buzz/api/teams.py` whitelisted API
- Role fixtures for `Event Manager` and `Frontdesk Manager` (currently referenced in 22 doctype
  perm blocks but never exported — `fixtures/role.json` only has `Buzz User` + `Frontdesk Manager`)
- `active_team` field on the existing `Event User Preferences` doctype
- Install/migrate hook: default team for existing Event Manager users

### Out (deferred to)
- `team` field on any event doctype → `02-team-field-on-events-and-backfill.md`
- Permission enforcement → `03-permission-hooks.md`
- Invitations → `04-team-invitations.md`

## Backend changes

### New doctype: `Buzz Team` (module: Events)

| fieldname | type | options | notes |
|---|---|---|---|
| `team_name` | Data | reqd, in list view | display name |
| `slug` | Data | unique | autoslug from team_name in `before_insert`; reserved for public host pages later |
| `logo` | Attach Image | | |
| `owner_user` | Link | User, reqd, read-only | creator; set in `before_insert` |

Naming: `autoname: format:TEAM-{####}` (slug stays a mutable display handle).
Controller `after_insert`: create `Buzz Team Membership` (owner_user, `team_role=Owner`,
`status=Active`).

### New doctype: `Buzz Team Membership` (module: Events)

| fieldname | type | options | notes |
|---|---|---|---|
| `team` | Link | Buzz Team, reqd | |
| `user` | Link | User, reqd | |
| `team_role` | Select | Owner\nAdmin\nManager\nFrontdesk\nViewer | reqd, default Manager |
| `status` | Select | Active\nDisabled | default Active |

Constraints & controller:
- `validate`: uniqueness of `(team, user)` (`frappe.db.exists` check + unique index via
  `unique` constraint in migration or `autoname: format:{team}-{user}` — pick unique index).
- `on_update` + `after_insert`: sync Frappe roles per the matrix in `00-plan.md`
  (`Owner/Admin/Manager` → add `Event Manager`; `Frontdesk` → add `Frontdesk Manager`). Never
  remove roles automatically (user may hold them via another team) — recompute across all Active
  memberships of that user in a helper `buzz.teams.sync_frappe_roles(user)`.
- `validate`: a team must always retain at least one Active `Owner` (block demote/disable of the
  last owner).

### `buzz/teams.py` (new domain module)

- `create_team(team_name: str) -> Buzz Team` — creates team (+ owner membership via controller).
- `get_teams_for_user(user: str) -> list[dict]` — Active memberships joined to team
  (name, team_name, slug, logo, team_role) via `frappe.get_all` on membership + team fields.
- `get_membership(team: str, user: str) -> dict | None` — Active membership row or None.
- `sync_frappe_roles(user: str)` — see above.
- `create_default_team_for(user: str)` — idempotent; used by install hook.

### `buzz/api/teams.py` (new API module — organizer APIs get their own files, do not grow `buzz/api/__init__.py`)

All `@frappe.whitelist()`, no guest access.

### `Event User Preferences` change

Add field `active_team` (Link → Buzz Team). Doctype currently has a single `user` field and is
already per-user. `set_active_team` validates the caller has an Active membership in that team.

### Install & fixtures

- `fixtures/role.json`: add `Event Manager` (desk_access 0 in v2 posture; keep existing entries).
- `buzz/install.py` `after_install` + a patch `buzz/patches/create_default_teams.py`
  (registered in `patches.txt`): for each enabled user holding `Event Manager`, call
  `create_default_team_for(user)` with team name `{first_name}'s Team`. Idempotent.

## Frontend changes

None. (Consumed by `01-dashboard/01`.)

## API contract

| Endpoint | Method | Params | Returns | Auth |
|---|---|---|---|---|
| `buzz.api.teams.create_team` | POST | `team_name` | `{name, team_name, slug}` | any logged-in user |
| `buzz.api.teams.get_my_teams` | GET | — | `[{name, team_name, slug, logo, team_role}]` | logged-in |
| `buzz.api.teams.get_active_team` | GET | — | `{name, team_name, slug, logo, team_role}` or null; falls back to first membership | logged-in |
| `buzz.api.teams.set_active_team` | POST | `team` | `{ok: true}` | member of `team` |

## Permissions notes

- Doctype perms: `Buzz Team` + `Buzz Team Membership` readable by `Buzz User` role (row-level
  scoping arrives in step 03); write via API only (`System Manager` full access in Desk).
- `create_team` is open to any logged-in user — this is the self-serve entry point.

## Demo script

1. `bench --site buzz.localhost console`: create users `alice@x.com`, `bob@x.com`.
2. As alice (API): `create_team("Alice Events")` → team + Owner membership exist.
3. As alice: `get_my_teams()` → exactly one team, `team_role == "Owner"`; alice now holds
   `Event Manager` role.
4. As bob: `get_my_teams()` → `[]`; `set_active_team(<alice's team>)` → throws.
5. `bench migrate` on a site with an existing Event Manager user → default team created once;
   re-running the patch is a no-op.

## Acceptance criteria (merge gate)

### Automated tests — `buzz/tests/test_teams.py` (new)
`bench --site buzz.localhost run-tests --module buzz.tests.test_teams`
- `create_team` creates the team + Owner membership + grants `Event Manager` to creator.
- Duplicate `(team, user)` membership insert raises.
- Role sync: adding Frontdesk membership grants `Frontdesk Manager`; demoting the only Owner /
  disabling the last Active Owner membership raises.
- `get_my_teams` returns only the caller's Active memberships (two-user isolation case).
- `set_active_team` for a non-member raises; for a member persists to `Event User Preferences`.
- `create_default_team_for` is idempotent (call twice → one team).
- Patch `create_default_teams` run twice → no duplicates.

### Browser checks (agent-browser)
None — no UI in this step (covered by `01-dashboard/01` checks).

## Dependencies & risks

- `Event Manager` fixture must not clobber existing site roles — fixture export merges by name.
- Role sync is additive-only by design; revocation handled in `sync_frappe_roles` recompute.
