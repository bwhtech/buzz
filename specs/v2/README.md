# Buzz v2 Specs

Buzz v2 turns Buzz from a single-tenant, Desk-administered event app into a **multi-tenant,
self-serve event platform**. Two pillars are specced here as tracer-bullet step sequences:

| Folder | Pillar |
|---|---|
| [`00-teams/`](00-teams/00-plan.md) | Teams & multi-tenancy — the foundation. `Buzz Team` + `Buzz Team Membership`, tenant field cascade, permission hooks, invitations. |
| [`01-dashboard/`](01-dashboard/00-plan.md) | Unified manager + attendee dashboard — Frappe UI app shell, event workspace, Desk parity for organizers, Pulse product analytics. |
| [`02-speaker-remodel.md`](02-speaker-remodel.md) | **OPEN — decision pending.** Speaker model exploration: per-event speaker vs global profile. Must be finalized before `01-dashboard/10`. |

## Conventions

- **One step file = one PR-sized, independently demoable vertical slice.** Filename number = merge order within its folder.
- Each folder has a `00-plan.md` index (step order, dependencies, scope map).
- Every step file starts with a front-matter table: `Phase | Depends on | Status`.
- Status values: `Draft` → `Ready` → `In Progress` → `Done`.

## Cross-folder build sequence

```
00-teams/01 ─► 00-teams/02 ─► 00-teams/03 ─┐
                                           ├─► 01-dashboard/01 ─► 01-dashboard/02   (tracer bullet demo)
                                           │
00-teams/04 (invitations) ─────────────────┴─► 01-dashboard/03 … 14  (parity phases B–D)
```

Teams steps 01–03 land first (doctypes → tenant field → permissions), then the dashboard tracer
bullet (shell + events list + ticket type CRUD) proves the whole architecture end to end. Team
invitations (00-teams/04) are deliberately deferred until after the tracer bullet — not needed for
the first demo. Dashboard phases B–D then march to Desk parity.

## Step file template

```markdown
# NN — <Step title>

| Phase | Depends on | Status |
|---|---|---|
| A/B/C/D | <step files> | Draft |

## Goal
1–2 sentences: the thin vertical slice and why it's next.

## Demo criteria (definition of done)
What a reviewer sees working end to end, phrased as the demo.

## Scope
### In
### Out (deferred to)

## Backend changes
Doctypes (field tables), hooks.py keys, API signatures, patches, fixtures.

## Frontend changes
Routes added to router.ts, pages/components (frappe-ui component names), src/data/*.ts modules.

## API contract
| Endpoint (dotted path) | Method | Params | Returns | Auth |

## Permissions notes
Who can do what; guest/attendee flows that must not regress.

## Demo script
Numbered manual QA steps (exact URLs, expected outcomes).

## Acceptance criteria (merge gate)
### Automated tests
`bench --site buzz.localhost run-tests --module ...` targets + the cases they must cover.
### Browser checks (agent-browser)
Scripted agent-browser flows against the local site (dev server :8080 for frontend work).

## Dependencies & risks
```

### Acceptance-criteria conventions

- **Every step is merge-gated by its Acceptance criteria section** — Demo script is the human
  walkthrough; acceptance criteria are the strict, repeatable checks.
- **Unit/integration tests**: live in `buzz/tests/` (or doctype `test_*.py`), run via
  `bench --site buzz.localhost run-tests --module <module>`. Backend steps must ship tests in the
  same PR; a step whose tests are listed here but missing from the PR is incomplete.
- **Browser checks**: executed with **agent-browser** (`agent-browser --help`) against the local
  site — frontend steps target the vite dev server on `:8080`, public/attendee flows target the
  site directly. Each check is written as a concrete flow (URL → actions → asserted outcome) so it
  can be replayed verbatim. Run headed locally; headless is fine for CI.
- **Cross-tenant checks always use two seeded teams** (team A / team B with one event each) —
  seed via a shared test fixture/factory so browser and unit checks agree on data.

## Global assumptions

1. **frappe-ui v1 beta migration is a prerequisite** (`DesktopShell`, `frappe-ui/list`,
   `useCall`/`useList`/`useDoc`, semantic tokens, `telemetryPlugin`). `dashboard/package.json`
   currently pins `frappe-ui ^0.1.257` — the Step-0 checklist in `01-dashboard/00-plan.md` gates
   Phase A on the upgrade being merged.
2. **Single SPA.** Manager area grafts onto the existing dashboard app under `/manage/*`;
   attendee (`/account/*`) and public booking routes stay intact.
3. **Teams are the tenant boundary.** Every organizer-facing record belongs to a `Buzz Team`;
   permissions derive from `Buzz Team Membership`, not global roles alone.
4. **No Desk for organizers** at the end of Phase D; Desk remains for System Managers.
