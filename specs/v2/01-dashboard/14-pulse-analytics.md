# 14 — Product analytics (Pulse)

| Phase | Depends on | Status |
|---|---|---|
| Cross-cutting (init after 01, instrument as steps land) | 01-dashboard/01 | Draft |

## Goal

Product analytics via **Frappe Pulse**, exactly the way Frappe CRM does it on current develop:
the `telemetryPlugin` that ships inside frappe-ui v1 beta + capture call sites. Near-zero backend
code — boot config, client loading, and ingest all live in frappe / frappe-ui / the Pulse service.

## How it works (verified against frappe/crm develop + frappe-ui main)

- frontend init: `app.use(telemetryPlugin, { app_name: 'buzz' })` — plugin from
  `frappe-ui/frappe` (`frappe/telemetry/index.ts`).
- The plugin fetches boot config from the whitelisted framework method
  `frappe.utils.telemetry.pulse.client.boot_config`, which returns enabled/host/key/site only when
  site config has `pulse_api_key` **and** System Settings `enable_telemetry` is on
  (or `pulse_force_enabled`). Without config it returns `{enabled: false}` → the plugin no-ops.
- The Pulse client JS is dynamically imported at runtime from the pulse host
  (default `https://pulse.m.frappe.cloud/assets/pulse/js/pulse_client.js`); origin-validated.
- Components: `const { capture } = useTelemetry()` then `capture('event_created', {...})` —
  **bare snake_case event names**, no app prefix (`app_name` is passed separately on every event).
- Server-side captures: `from frappe.utils.telemetry import capture; capture("active_site", "buzz")`.

## Demo criteria (definition of done)

On a staging site with `pulse_api_key` configured: creating an event produces an `event_created`
event visible in the Pulse dashboard attributed to app `buzz`. On an unconfigured site: zero
console errors, zero network noise beyond the one boot_config call.

## Scope

### In
- Plugin init + `useTelemetry` capture call sites across manager + attendee flows
- Optional daily server-side `active_site` heartbeat
### Out (deferred to)
- Publisher-facing event analytics (page views/funnels) — separate future pillar
- Self-hosted Pulse — supported via `pulse_host` site config, no code change; not set up here

## Backend changes

Optional, tiny: `buzz/tasks.py` daily job → `capture("active_site", "buzz")` (mirrors CRM's
`crm/www/crm.py`). Nothing else — no doctypes, no endpoints.

## Frontend changes

- `dashboard/src/main.ts`: `import { telemetryPlugin } from 'frappe-ui/frappe'` +
  `app.use(telemetryPlugin, { app_name: 'buzz' })` (pass `router` for pageview tracking on new
  sites, mirroring CRM).
- Capture call sites — the **event registry** (single source of truth; add rows as steps land):

| Event name | Where (step) | Properties |
|---|---|---|
| `team_created` | onboarding + switcher create (01) | — |
| `event_created` | NewEventDialog (01) | `{from_template: bool}` |
| `event_published` / `event_unpublished` | Overview (03) | — |
| `ticket_type_created` | TicketTypeDialog (02) | — |
| `coupon_created` | CouponDialog (04) | `{coupon_type}` |
| `add_on_created` | AddOnDialog (05) | — |
| `sponsor_added` / `sponsorship_tier_created` | Sponsors tab (06) | — |
| `offline_payment_confirmed` | Bookings (07) | — |
| `attendees_exported` | Attendees (07) | — |
| `attendee_checked_in` | Check-in (08) | `{manual: bool}` |
| `member_invited` | Invites (13) | `{team_role}` |
| `member_role_changed` / `member_removed` | Members (13) | — |
| `template_created` / `event_created_from_template` | Templates (11) | — |
| `booking_initiated` / `booking_completed` | attendee BookingForm flow | `{is_guest, has_coupon}` |
| `ticket_transferred` / `cancellation_requested` | attendee TicketDetails | — |

- Convention: capture **after** the mutation succeeds (in the `await`ed success path), never on
  click. No PII in properties (no emails/names); team/user identity comes from Pulse's own
  anonymized boot identity.

## API contract

No new endpoints (uses framework `boot_config`).

## Permissions notes

Telemetry is opt-in at the site level (`enable_telemetry` + `pulse_api_key`). Nothing captured for
sites that don't opt in. Anonymous mode handled by the SDK (cookieless default).

## Demo script

1. Unconfigured dev site: boot → one `boot_config` call returning `{enabled: false}`; no errors.
2. Staging with `pulse_api_key`: create team + event + ticket type → three events visible in the
   Pulse dashboard under app `buzz`.
3. Grep check: every `capture(` call site uses a name from the registry table above.

## Acceptance criteria (merge gate)

### Automated tests
- Registry lint (CI grep or small pytest): every `capture('...')` call site in `dashboard/src`
  uses an event name present in this file's registry table; fails on unknown names.
- Backend heartbeat (if shipped): scheduler job calls `frappe.utils.telemetry.capture` — smoke
  test that it no-ops without config (no exception).

### Browser checks (agent-browser, dev server :8080)
1. Unconfigured dev site: load `/dashboard/manage/events` → read console messages → zero
   telemetry errors; network log shows exactly one `boot_config` call returning
   `{enabled: false}` and no pulse-host requests.
2. Configured staging site (`pulse_api_key` + `enable_telemetry`): create team → event → ticket
   type in the UI → network log shows capture requests to the pulse host for `team_created`,
   `event_created`, `ticket_type_created`; events visible in the Pulse dashboard under app
   `buzz`.
3. Capture timing: cancel the New Event dialog → no `event_created` fired (success-path-only
   convention holds).

## Dependencies & risks

- Requires frappe version with `frappe.utils.telemetry.pulse` (present on this bench's frappe
  develop) and frappe-ui v1 beta (Step-0 gate).
- Registry drift: PR review rule — new capture call sites must update the table in this file.
