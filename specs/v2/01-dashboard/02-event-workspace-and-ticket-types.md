# 02 — Event workspace & ticket types

| Phase | Depends on | Status |
|---|---|---|
| A | 01-dashboard/01 | Draft |

## Goal

Complete the tracer bullet: open an event into a tabbed workspace and manage `Event Ticket Type`
CRUD without Desk — the first full manage-to-public loop.

## Demo criteria (definition of done)

Manager opens their event → Tickets tab → creates "Early Bird ₹499, 100 available" → opens the
public `/dashboard/book-tickets/:route` page → the new ticket type is purchasable. A manager from
another team opening this event's URL gets 403.

## Scope

### In
- Event workspace frame with full tab registry (only Overview-stub + Tickets enabled)
- Ticket types table + create/edit dialog + publish toggle + delete
### Out (deferred to)
- Real Overview content → step 03; every other tab → its step

## Backend changes

**None.** Plain `frappe.client` CRUD through `useList`/`useDoc`, protected by role perms + team
hooks. The spec asserts this deliberately: if a bespoke endpoint proves necessary for basic CRUD,
that's a smell in the permission layer — fix `00-teams/03` instead.

## Frontend changes

### Routes

| Path | Name | Meta |
|---|---|---|
| `/manage/events/:eventId` | `EventWorkspace` (redirects to `overview`) | `requiresTeam` |
| `/manage/events/:eventId/:tab` | child views | `requiresTeam` |

### Components

- `src/pages/manage/EventWorkspace.vue` — header: `Breadcrumbs` (Events / {title}), status `Badge`,
  "View page" `Button variant="ghost"` (→ public route, new tab). `Tabs` bound to the route param;
  full registry from `00-plan.md` tab map, tabs whose step hasn't landed render disabled with a
  "soon" tooltip. Loads the event once via `useDoc("Buzz Event", eventId)` and provides it to tabs.
- `src/pages/manage/event/OverviewTab.vue` — stub: event title/date summary card only.
- `src/pages/manage/event/TicketTypesTab.vue` — `List`: title, price (`tabular-nums`, formatted
  via `format_currency`), sold/available (`tickets_sold` / `max_tickets_available`), remaining,
  published `Badge`; row actions `Dropdown`: Edit, Publish/Unpublish, Delete (imperative
  `dialog.confirm` → `toast`). Header `Button` "New Ticket Type".
- `TicketTypeDialog.vue` — `Dialog v-model:open`; `FormControl`s mapped to real fields:
  `title` (reqd), `price` + `currency` (Link Currency), `max_tickets_available` (Int),
  `auto_unpublish_after` (DatePicker), `is_published` (Switch). Create + edit modes share it.

### Data layer

- `src/data/tickets.ts` — `useList({ doctype: "Event Ticket Type", filters: { event } })` with
  insert/update/delete helpers.

## API contract

No new endpoints.

## Permissions notes

- Manager/Admin/Owner can CRUD; Viewer sees the tab read-only (hide mutating buttons by
  `team_role` from `activeTeam`); server denies regardless.
- `tickets_sold` / `remaining_tickets` are system-maintained — read-only in the dialog.

## Demo script

1. `/manage/events` → click event → workspace opens on Overview stub, Tickets tab enabled.
2. New Ticket Type: "Early Bird", 499 INR, 100 available, published → row appears, toast.
3. Public booking page for the event → Early Bird listed and bookable (complete a test booking).
4. Unpublish it → gone from public page; sold counters unaffected.
5. As bob (team B): open the same workspace URL → 403 page.

## Acceptance criteria (merge gate)

### Automated tests
None new (step asserts zero bespoke endpoints). `test_team_permissions` parametrized case for
`Event Ticket Type` covers the CRUD authorization; extend it if the tracer bullet exposes gaps.

### Browser checks (agent-browser, dev server :8080)
1. Manager → open event → assert workspace header (breadcrumbs, status badge) + tab strip with
   Tickets enabled and roadmap tabs disabled.
2. Create ticket type "Early Bird", 499 INR, 100 available, published → row appears with correct
   formatted price and 0/100 sold.
3. Public page `/dashboard/book-tickets/<route>` (fresh session) → "Early Bird" listed; complete
   a booking → Tickets tab shows sold count 1.
4. Unpublish via row action → public page no longer offers it.
5. Edit dialog: `tickets_sold`/`remaining_tickets` rendered read-only.
6. Viewer-role member → Tickets tab visible, no New/Edit/Delete controls; direct mutation via
   console `useList.insert` equivalent (REST call) → server 403.
7. Team-B manager → workspace URL → 403 page.

## Dependencies & risks

- Delete of a ticket type with sold tickets: framework link validation will throw —
  surface the server message via `toast.error`, don't pre-empt client-side.
- **Tracer bullet exit criteria:** after this step, architecture review before Phase B fan-out.
