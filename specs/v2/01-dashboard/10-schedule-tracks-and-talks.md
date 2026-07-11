# 10 — Schedule, tracks & talks

| Phase | Depends on | Status |
|---|---|---|
| D | 01-dashboard/03 | Draft |

## Goal

Desk parity for the agenda: Schedule tab managing `Event Track`, `Schedule Item` (child table on
Buzz Event), `Event Talk`, plus a read-and-accept inbox for `Talk Proposal` submissions.
(CRUD parity only — the drag-drop visual builder remains a future pillar.)

## Demo criteria (definition of done)

Manager builds a 2-track half-day schedule; the public schedule rendering shows it. Accepting a
talk proposal creates an `Event Talk` that can be slotted.

## Scope

### In
- Tracks chips CRUD; schedule items list grouped by day → time; talk CRUD with speakers
- Proposals inbox: list + detail + Accept/Reject
### Out (deferred to)
- Gantt/timeline drag-drop builder → future "schedule builder" pillar
- Speaker Profile management (attendee-owned) → Phase E

## Backend changes

`buzz/api/talks.py` (new):

```python
@frappe.whitelist()
def accept_talk_proposal(proposal: str) -> dict:
    """Sets Talk Proposal status Approved; creates Event Talk (+ Talk Speaker child rows
    from Proposal Speaker). Returns the new talk name. Manager+ on the event's team.
    Reuses existing controller logic if present — audit talk_proposal.py first."""
```

(If the accept transition already exists on the doctype controller, the endpoint is a thin wrapper.)

## Frontend changes

- `src/pages/manage/event/ScheduleTab.vue` — three stacked sections:
  1. **Tracks** — chip row (`Badge`-styled) + add/rename/delete (`dialog.prompt`).
  2. **Schedule** — `Schedule Item` rows grouped by date, sorted by start time: time range
     (`tabular-nums`), title, track chip, linked talk. Row edit dialog: date, start/end time,
     title, track Select, talk Link. Saved through the parent `Buzz Event` doc
     (`useDoc` child-table update).
  3. **Talks** — `List` of `Event Talk`: title, speakers (Avatars), track, status. `TalkDialog`:
     title, description (`Editor`), track, speakers child editor (Link → Speaker Profile).
- **Proposals inbox** — collapsible section: pending `Talk Proposal` rows (title, speaker,
  submitted); detail slide-over with full submission; `Button` Accept (→ `accept_talk_proposal`,
  toast + talk appears) / Reject (`dialog.confirm`, sets status).
- `data/schedule.ts`, `data/talks.ts`.

## API contract

| Endpoint | Method | Params | Returns | Auth |
|---|---|---|---|---|
| `buzz.api.talks.accept_talk_proposal` | POST | `proposal` | `{talk}` | team Manager+ |

## Permissions notes

`Talk Proposal` is attendee-submitted (owner = speaker) — team members read via team scoping
(cascade stamps team from event); speakers keep editing their own (existing
`allow_editing_talks_after_acceptance` behavior untouched).

## Demo script

1. Add tracks "Main Hall", "Workshop".
2. Create 4 schedule items across two dates → grouped rendering correct.
3. Submit a talk proposal via the public flow → appears in inbox.
4. Accept → `Event Talk` created with speakers; slot it into a schedule item.
5. Public schedule (where rendered) shows the agenda.

## Acceptance criteria (merge gate)

### Automated tests — `buzz/tests/test_talks.py` (new)
`bench --site buzz.localhost run-tests --module buzz.tests.test_talks`
- `accept_talk_proposal`: proposal with 2 `Proposal Speaker` rows → status Approved, `Event Talk`
  created with matching speakers; second call raises (already accepted); Viewer/cross-team caller
  raises.
- Reject path sets status without creating a talk.
- Speaker-side edit-after-acceptance behavior unchanged
  (`allow_editing_talks_after_acceptance` on/off).

### Browser checks (agent-browser, dev server :8080)
1. Schedule tab → add tracks "Main Hall", "Workshop" → chips render.
2. Create 4 schedule items across 2 dates → grouped by date, sorted by time
   (assert order in DOM).
3. Fresh session → submit talk proposal via public flow → inbox shows it pending.
4. Accept from slide-over → toast, talk appears in Talks section with speakers; slot it into a
   schedule item.
5. Public schedule rendering shows both tracks and the slotted talk.

## Dependencies & risks

- `Schedule Item` is a child table — mutations go through the parent event doc save; concurrent
  edits overwrite (single-editor assumption fine for now, note it).
- Audit existing `talk_proposal.py` controller before writing the accept endpoint — logic may
  already exist Desk-side.
