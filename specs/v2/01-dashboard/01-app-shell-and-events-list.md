# 01 — App shell & events list

| Phase | Depends on | Status |
|---|---|---|
| A | 00-teams/01–03, Step-0 gate | Draft |

## Goal

First pixels of the manager app: frappe-ui app shell with sidebar + team switcher, and a
team-scoped events list with event creation. Proves teams, permissions, routing, and the new
frappe-ui stack in one slice.

## Demo criteria (definition of done)

A manager logs in, lands on `/manage/events`, sees only their active team's events, switches team
from the sidebar and the list swaps, creates an event from a dialog and it appears in Desk with the
correct team. A user with no team gets the "Create your team" onboarding. Attendee routes
unaffected.

## Scope

### In
- `ManagerLayout` shell (desktop + mobile), sidebar nav skeleton, team switcher
- Events list page + New Event dialog
- No-team onboarding screen; 403 page for non-member deep links
- `data/teams.ts`, `data/events.ts`

### Out (deferred to)
- Event workspace → step 02
- Sidebar items Venues/Hosts/Templates/Team Settings render disabled → steps 09/11/13

## Backend changes

None. Consumes `buzz.api.teams.*` (00-teams/01); list scoping comes free from permission hooks.

## Frontend changes

### Routes (`dashboard/src/router.ts`)

| Path | Name | Meta |
|---|---|---|
| `/manage` | redirect → `/manage/events` | `requiresTeam` |
| `/manage/events` | `ManageEventsList` | `requiresTeam` |
| `/manage/onboarding` | `TeamOnboarding` | logged-in only |
| `/manage/403` | `ManageForbidden` | |

All under a parent route rendering `ManagerLayout` as a lazy chunk. Router guard: resolve
`data/teams.ts` `myTeams` once → empty ⇒ redirect onboarding.

### Components

- `src/layouts/ManagerLayout.vue` — `DesktopShell` / `MobileShell` split per DESIGN.md shell
  anatomy. `Sidebar` (~14rem): header = **team switcher** `Dropdown` (team logo `Avatar`,
  `team_name`, chevron; items from `myTeams`, active check, "Create team" action) →
  `set_active_team` then invalidate all manager lists; nav `SidebarItem`s: Events
  (`lucide-calendar`), Venues, Hosts, Templates, Team Settings (disabled until their steps);
  footer: "Attendee view" link → `/account/bookings`, user `Dropdown` (logout).
- `src/pages/manage/EventsList.vue` — data-table archetype: `PageHeader` (title "Events", primary
  `Button variant="solid"` "New Event"), `List` from `frappe-ui/list` with columns: title,
  `start_date` (formatted), venue, status `Badge` (`is_published` → green "Live" / gray "Draft"),
  tickets sold. Row click → step 02 workspace (until then, no-op). `#empty` slot: illustration +
  "Create your first event" CTA.
- `NewEventDialog.vue` — `Dialog v-model:open`; `FormControl`s: title (reqd), start_date /
  end_date (`DatePicker`), category (Link to `Event Category`), medium Select. Insert via
  `events.ts` with `team: activeTeam` stamped; `toast.success` + route to the new event.
- `src/pages/manage/TeamOnboarding.vue` — centered card: team name input → `create_team` →
  redirect `/manage/events`.

### Data layer

- `src/data/teams.ts` — `useCall` wrappers: `myTeams`, `activeTeam` (+ `setActiveTeam(team)` that
  awaits the POST then invalidates manager caches).
- `src/data/events.ts` — `useList({ doctype: "Buzz Event", fields: [...], filters: { team } })`
  + `insertEvent`.

## API contract

Consumes `buzz.api.teams.get_my_teams`, `get_active_team`, `set_active_team`, `create_team` only.

## Permissions notes

List scoping enforced server-side by `00-teams/03` — the `team` filter in `useList` is UX
(active-team narrowing), not security. Non-member deep link → server 403 → render `ManageForbidden`.

## Demo script

1. `yarn dev` (:8080), log in as alice (Owner, team A with 2 events) → `/manage/events` lists 2.
2. Sidebar switcher → team X (alice also member) → list swaps without reload.
3. "New Event" → fill dialog → toast, event visible; Desk shows it with `team = X`.
4. Log in as dave (no teams) → `/manage` → onboarding → create team → empty events list.
5. `/account/bookings` and public `/book-tickets/:route` unchanged.

## Acceptance criteria (merge gate)

### Automated tests
None new (no backend). Teams suites (`test_teams`, `test_team_permissions`) must still pass.

### Browser checks (agent-browser, dev server :8080)
1. Log in as team-A manager → `http://localhost:8080/dashboard/manage/events` → assert sidebar
   renders (team switcher shows team A name; nav items Events enabled, Venues/Hosts/Templates/
   Team Settings disabled) and list shows exactly team A's seeded events.
2. Team switcher → select team X → assert events list swaps without full reload (URL unchanged).
3. "New Event" → fill title + start date → submit → toast appears, row appears; assert via Desk
   API that the doc's `team` == active team.
4. Log in as user with no teams → `/dashboard/manage` → assert redirect to onboarding screen;
   create team → lands on empty events list with CTA.
5. Log in as team-B manager → paste team-A workspace URL → assert 403 page (not blank/error).
6. Regression: `/dashboard/account/bookings` renders; public `/dashboard/book-tickets/<route>`
   booking form loads.
7. Mobile viewport (390px): shell switches to `MobileShell`; nav reachable; list usable.

## Dependencies & risks

- Step-0 gate (frappe-ui v1 beta) is a hard blocker.
- Team switcher cache invalidation: central `invalidateManagerData()` helper in `teams.ts` from
  day 1, or stale cross-team data will leak into the UI (cosmetic, not security).
