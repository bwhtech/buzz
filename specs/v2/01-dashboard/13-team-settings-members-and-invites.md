# 13 — Team settings, members & invites

| Phase | Depends on | Status |
|---|---|---|
| D | 00-teams/04, 00-teams/05, 01-dashboard/01 | Draft |

## Goal

Team administration UI: edit team profile, manage members and roles, invite by email, see/revoke
pending invitations.

## Demo criteria (definition of done)

Owner invites a colleague as Frontdesk from the UI; colleague accepts, appears in Members, logs in
and sees only the check-in surface. Owner changes a member's role and removes another.

## Scope

### In
- Team settings dialog (settings-dialog archetype): General, Members, Invites sections
- Role change / remove member / leave team
### Out (deferred to)
- Ownership transfer flow — explicit future step (Owner role not assignable via invite/role change)
- Billing/plans — future pillar

## Backend changes

`buzz/api/teams.py` additions:

```python
@frappe.whitelist()
def get_team_members(team) -> list  # Active memberships + user full_name, avatar; member-visible

@frappe.whitelist()
def update_member_role(team, user, team_role)  # Owner/Admin; cannot touch Owner rows; not to Owner

@frappe.whitelist()
def remove_member(team, user)  # Owner/Admin; sets membership Disabled; cannot remove last Owner

@frappe.whitelist()
def update_team(team, team_name=None, logo=None)  # Owner only

@frappe.whitelist()
def leave_team(team)  # any member except last Owner
```

Role revocation on remove/demote goes through `buzz.teams.sync_frappe_roles(user)` (recompute
across remaining memberships).

## Frontend changes

- Sidebar: enable "Team Settings" (`lucide-settings`), opens `TeamSettingsDialog.vue`
  (settings-dialog archetype: left nav list, right content pane, `Dialog` size xl):
  - **General** — team name `FormControl`, logo `FileUploader`, slug (read-only display),
    danger zone: Leave team (`dialog.confirm`).
  - **Defaults** — `Buzz Team Settings` (00-teams/05) bound via
    `useDoc("Buzz Team Settings", team)`: transfer/add-on/cancellation window Ints, support
    email, `default_ticket_email_template` + sponsor-deck defaults (Email Template Links,
    reply-to, cc, `auto_send_pitch_deck` Switch). Owner/Admin editable; others read-only.
  - **Members** — `List`: `Avatar`, full name, email, `team_role` — inline `Select` editable by
    Owner/Admin (disabled on Owner rows), remove action (`dialog.confirm`).
  - **Invites** — "Invite member" row: email `FormControl` + role `Select`
    (Admin/Manager/Frontdesk/Viewer) + `Button` "Send invite" → `invite_member`; pending list
    (email, role, sent time) with Revoke.
- `data/teams.ts` additions: members/invites `useList`-style calls + mutations.

## API contract

| Endpoint | Method | Params | Returns | Auth |
|---|---|---|---|---|
| `buzz.api.teams.get_team_members` | GET | `team` | `[{user, full_name, user_image, team_role, status}]` | team member |
| `buzz.api.teams.update_member_role` | POST | `team, user, team_role` | `{ok}` | Owner/Admin |
| `buzz.api.teams.remove_member` | POST | `team, user` | `{ok}` | Owner/Admin |
| `buzz.api.teams.update_team` | POST | `team, team_name?, logo?` | `{ok}` | Owner |
| `buzz.api.teams.leave_team` | POST | `team` | `{ok}` | member |
| (from 00-teams/04) `invite_member`, `get_pending_invitations`, `revoke_invitation` | | | | Owner/Admin |

## Permissions notes

All mutations double-guarded: UI hides controls by `team_role`, server validates via membership
lookups. Last-Owner protection lives in the membership controller (00-teams/01).

## Demo script

1. As Owner: Team Settings → rename team + upload logo → sidebar switcher updates.
2. Invites → invite `frank@x.com` as Frontdesk → pending row appears.
3. Frank accepts → Members shows Frank (Frontdesk); Frank's session: check-in-only nav (step 08).
4. Change Frank → Viewer → his next load shows read-only workspace.
5. Remove Frank → memberships Disabled; Frank's `/manage` → onboarding screen.
6. As Manager-role member: settings dialog shows Members read-only, no invite form.

## Acceptance criteria (merge gate)

### Automated tests — extend `buzz/tests/test_teams.py`
- `update_member_role`: Owner/Admin succeeds; Manager raises; targeting an Owner row raises;
  promoting to Owner raises.
- `remove_member`: sets Disabled; last-Owner removal raises; role recompute — user in two teams
  keeps `Event Manager` when removed from one, loses it when removed from both.
- `leave_team`: member succeeds; last Owner raises.
- `update_team`: Owner succeeds; Admin raises.

### Browser checks (agent-browser, dev server :8080)
1. Owner → Team Settings dialog → General: rename + logo upload → sidebar switcher label/avatar
   update.
2. Defaults section → change transfer window to 7 → saved; attendee-facing effect covered by
   `00-teams/05` check 1 (re-run it here).
3. Invites → invite `frank@x.com` as Frontdesk → pending row appears; accept in fresh session →
   Members shows Frank (Frontdesk).
4. Frank's session → sidebar trimmed to check-in surface (cross-check with step 08 criteria).
5. Change Frank → Viewer → his next page load shows read-only workspace; remove Frank → his
   `/dashboard/manage` shows onboarding.
6. Manager-role member → Members list read-only, no invite form, no Defaults editing.

## Dependencies & risks

- Role sync recompute on remove/demote is the fiddly bit — test a user in two teams keeping
  `Event Manager` when removed from one.
