# 01-dashboard — Plan

Unified dashboard: one SPA serving attendees (existing `/account/*` + public booking routes,
untouched) **and** event managers (new `/manage/*` area). Goal of phases A–D: **Desk parity** —
an organizer never opens `/app`.

## Step 0 — prerequisite gate (frappe-ui v1 beta)

All specs below are written against **frappe-ui v1 beta** APIs. `dashboard/package.json` currently
pins `frappe-ui ^0.1.257` — **Phase A must not start until the migration is merged.** Verification
checklist:

- [ ] `package.json` pins the v1 beta release; `yarn build` green
- [ ] `import { DesktopShell } from 'frappe-ui'` resolves and renders in a scratch page
- [ ] `frappe-ui/list` subpath (`List`, `ListRow`) importable
- [ ] `useCall` / `useList` / `useDoc` available
- [ ] Semantic tokens compile (`bg-surface-base`, `text-ink-gray-9`, `border-outline-gray-2`)
- [ ] `Dialog v-model:open`, imperative `toast` / `dialog` helpers work
- [ ] `telemetryPlugin` exported from `frappe-ui/frappe` (needed by step 14)
- [ ] Existing attendee pages still function (booking flow smoke test on :8080)

## Conventions (binding for all steps)

**Routing** — manager area under `/manage/*` in `dashboard/src/router.ts`, lazy-loaded chunk
(`() => import(...)`), guarded by `meta: { requiresTeam: true }`; the router guard resolves
`get_my_teams` once (cached) — no teams → onboarding screen; not logged in → existing
`LoginRequired` handling. No team slug in URLs: team identity = active-team preference. Deep link
into another team's event → auto-switch active team if member, else 403 page.

**Data layer** — all new manager code uses `useList` / `useDoc` / `useCall` composables, organized
per domain in `dashboard/src/data/` (`teams.ts`, `events.ts`, `tickets.ts`, `bookings.ts`, …).
**No new inline `createResource`.** The 68 existing inline attendee resources are explicitly out of
scope — do not refactor them in these steps.

**UI language** — frappe-ui components only (`Button`, `Dialog`, `FormControl`, `List`, `Badge`,
`Dropdown`, `Tabs`, `FileUploader`, `Breadcrumbs`); semantic tokens only; icons via
`lucide-*` classes; espresso design per the frappe-ui skill `DESIGN.md` (shell anatomy, data-table
archetype, settings-dialog archetype).

**Backend** — plain doctype CRUD goes through `frappe.client` via `useList`/`useDoc` under the
team permission hooks (`00-teams/03`). Bespoke endpoints only for aggregation/validation, in
per-domain modules `buzz/api/<domain>.py`.

## Phases

| Phase | Steps | Outcome |
|---|---|---|
| **A — tracer bullet** | [01](01-app-shell-and-events-list.md), [02](02-event-workspace-and-ticket-types.md) | Shell + team-scoped events list + ticket type CRUD, end to end |
| **B — core workspace** | [03](03-event-overview-and-editing.md), [04](04-coupons.md), [05](05-ticket-add-ons.md), [06](06-sponsorship-tiers-and-sponsors.md) | Event fully configurable without Desk |
| **C — operations** | [07](07-bookings-and-attendees.md), [08](08-checkin-desk.md) | Money + people + door |
| **D — parity long tail** | [09](09-venues-hosts-library.md), [10](10-schedule-tracks-and-talks.md), [11](11-event-templates.md), [12](12-event-settings-payments-and-forms.md), [13](13-team-settings-members-and-invites.md) | Full Desk parity + team admin |
| **cross-cutting** | [14](14-pulse-analytics.md) | Pulse product analytics (init early, instrument as steps land) |

## Event workspace tab map

`/manage/events/:eventId` — tabs registered up front (step 02), enabled as steps land:

| Tab | Step | Manages |
|---|---|---|
| Overview | 03 | KPIs, core `Buzz Event` fields, publish |
| Tickets | 02 | `Event Ticket Type` |
| Add-ons | 05 | `Ticket Add-on` |
| Coupons | 04 | `Buzz Coupon Code` |
| Sponsors | 06 | `Sponsorship Tier`, `Event Sponsor`, enquiries (read) |
| Bookings | 07 | `Event Booking`, `Event Payment` |
| Attendees | 07 | `Event Booking Attendee` / `Event Ticket` |
| Check-in | 08 | `Event Check In` + scanner |
| Schedule | 10 | `Schedule Item`, `Event Track`, `Event Talk`, proposals inbox |
| Settings | 12 | gateways, tax, registration windows, custom fields/forms, extra pages |

## Desk-parity matrix

| Doctype | Home in dashboard | Step |
|---|---|---|
| Buzz Event | Events list + workspace | 01–03 |
| Event Ticket Type | Tickets tab | 02 |
| Buzz Coupon Code | Coupons tab | 04 |
| Ticket Add-on | Add-ons tab | 05 |
| Sponsorship Tier / Event Sponsor / Sponsorship Enquiry | Sponsors tab | 06 |
| Event Booking / Event Payment | Bookings tab | 07 |
| Event Ticket / Event Booking Attendee | Attendees tab | 07 |
| Event Check In | Check-in tab | 08 |
| Event Venue / Event Host | Library pages | 09 |
| Schedule Item / Event Track / Event Talk / Talk Proposal | Schedule tab | 10 |
| Event Template (+ children) | Templates page | 11 |
| Event Payment Gateway / Offline Payment Method / Buzz Custom Field / Buzz Event Form / Additional Event Page | Settings tab | 12 |
| Buzz Team / Buzz Team Membership / User Invitation / Buzz Team Settings | Team settings | 13 |

**Phase E candidates (not covered, stay Desk-only for now — parity claims carve these out):**
`Buzz Settings` (site-wide Single — global admin config only; tenant-facing fields move to
`Buzz Team Settings` per `00-teams/05`), `Event Featured Speaker`,
`Speaker Profile`, `Buzz Campaign` + `UTM Parameter`, `Event Feedback` (read-only report later),
`Event Proposal` moderation, `Ticket Cancellation Request` approval queue.
