# 02 — Speaker model remodel (exploration)

> **STATUS: OPEN — NO DECISION TAKEN.** This spec captures the problem, the options, and a leaning.
> The model must be finalized before `01-dashboard/10-schedule-tracks-and-talks.md` is implemented
> (it CRUDs talks/speakers) and before the teams permission inventory treats speaker doctypes as
> settled.

## 1. Current model

| Doctype | Shape | Notes |
|---|---|---|
| `Speaker Profile` | standalone, autoincrement | `user` (Link User), `display_name` (synced from User via `hooks.py:38` `on_update`), `designation`, `company`, `display_image`, `social_media_links` child |
| `Talk Speaker` | child of `Event Talk` | `speaker` (Link Speaker Profile) **+ its own `social_media_links` child** |
| `Proposal Speaker` | child of `Talk Proposal` | raw `first_name`, `last_name`, `email` — **no link to Speaker Profile** |
| `Event Featured Speaker` | child of `Buzz Event` | `speaker` (Link Speaker Profile) |

## 2. Problems

1. **Two disjoint speaker representations.** CFP submissions carry raw contact rows
   (`Proposal Speaker`); accepted talks carry profile links (`Talk Speaker`). The accept flow has
   to reconcile/dedupe them, and today doesn't — profiles and proposal speakers never meet.
2. **Profile requires a User.** Co-speakers without accounts have no clean home; `Proposal Speaker`
   only has an email.
3. **Global profile vs multi-tenant v2.** One global record: Team A edits a bio → Team B's public
   event page changes. Ownership is unanswered (`00-teams/00-plan.md` parks Speaker Profile as
   "attendee-owned, not team-scoped" — a dodge, not a decision).
4. **Per-event customization already leaking in.** `Talk Speaker.social_media_links` duplicates the
   profile's socials — an ad-hoc per-talk override. Real speakers tailor bio/headshot per event.
5. **`Event Featured Speaker` is a separate child table** for what is essentially a flag + ordering
   on the event's speakers.

## 3. Prior art (researched 2026-07)

Both major CFP/speaker platforms converged on **global person identity + per-event speaker
profile**:

- **pretalx** — `SpeakerProfile` exists per (user, event): per-event biography, per-event profile
  picture; bios from past events offered as suggestions on new submissions.
  ([data models](https://docs.pretalx.org/developer/interfaces/models/),
  [concepts](https://docs.pretalx.org/developer/architecture/concepts/))
- **Sessionize** — default profile auto-copied into each event submission, then edited *per event*;
  editing the default never touches existing events.
  ([speaker dashboard](https://sessionize.com/playbook/speaker-dashboard),
  [submit a session](https://sessionize.com/playbook/submit-your-session-for-an-event))

## 4. Options

### Option A — Per-event speaker record (pretalx/Sessionize model)

New **`Event Speaker`** doctype (standalone, team via cascade):

| fieldname | type | notes |
|---|---|---|
| `event` | Link Buzz Event, reqd | |
| `team` | Link Buzz Team, read-only | stamped via `inherit_team_from_event` |
| `full_name` | Data, reqd | |
| `email` | Data | identity key for find-or-create |
| `user` | Link User | optional — enables self-serve editing (CFP flow, `allow_editing_talks_after_acceptance`) |
| `designation`, `company` | Data | |
| `bio` | Text Editor | per-event |
| `photo` | Attach Image | per-event |
| `social_media_links` | Table Social Media Link | |
| `is_featured` | Check | replaces `Event Featured Speaker` |
| `featured_order` | Int | |

Consequences:
- `Talk Speaker` child → Link `Event Speaker`; drop its `social_media_links` child.
- `Event Featured Speaker` child table **deleted** (flag + order above).
- Proposal accept → find-or-create `Event Speaker` by `(event, email)` per `Proposal Speaker` row.
- "Copy from previous event" prefill action (the reuse UX pretalx/Sessionize ship).
- Global `Speaker Profile`: either **dropped**, or shrunk to a thin identity record used only for
  prefill suggestions.
- Migration patch: one `Event Speaker` per distinct (event, `Talk Speaker.speaker`) + featured
  rows; repoint children.

**Pros:** per-event bio/photo (industry standard); account-less speakers fine; clean team-scoped
permissions; dashboard Schedule tab CRUD gets simpler.
**Cons:** migration; mild duplication of a person across events (the accepted trade-off everywhere).

### Option B — Global profile + per-event override junction

Keep `Speaker Profile` canonical; junction holds override fields (bio, photo, socials). More
normalized, but every renderer resolves two levels, and non-overridden fields still leak across
teams. More moving parts than A for less benefit.

### Option C — Minimal patch, no remodel

Make `user` optional; key identity on email; auto-create profile from `Proposal Speaker` on accept;
drop `Talk Speaker` socials duplication. Cheap; solves neither multi-tenant ownership nor per-event
bios. Only defensible if speakers are out of v2 scope.

### Option D — Team-scoped speaker directory (library model)

`Speaker` belongs to a team (like Venues/Hosts in `01-dashboard/09`), reused across that team's
events. Great for repeat meetups; simple permissions. No per-event bio; a person speaking for two
teams = two records (Luma/Eventbrite behave this way).

**Hybrid D+A** (team directory record + per-event rows referencing it with bio override) is
possible but reintroduces B's two-level resolution complexity.

## 5. Current leaning (not a decision)

**Option A**, keeping the optional `user` link so CFP self-editing still works, and treating
"repeat speaker" reuse as a copy-from-previous-event action rather than a shared mutable record.
Revisit D if usage turns out meetup-heavy (same roster every month).

## 6. Open questions to finalize

1. Drop `Speaker Profile` entirely, or keep as thin prefill identity?
2. Does the speaker get a public self-view/edit page (pretalx-style) in v2, or is editing
   manager-only + CFP-flow-only?
3. `Proposal Speaker` — replace with early `Event Speaker` creation at submission time, or keep raw
   rows until accept? (Early creation pollutes the speaker list with rejected proposals.)
4. Featured speakers ordering UX — flag on speaker vs drag-ordered list on the event.
5. Where does speaker management live in the dashboard — inside the Schedule tab (step 10) or its
   own workspace tab?
