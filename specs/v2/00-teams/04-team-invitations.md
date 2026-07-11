# 04 — Team invitations

| Phase | Depends on | Status |
|---|---|---|
| Foundation | 00-teams/03 | Draft |

## Goal

Owners/Admins invite members by email with a team role, reusing Frappe's built-in
`User Invitation` (`frappe/core/doctype/user_invitation/`) — no bespoke invite doctype.

## Demo criteria (definition of done)

API-invite a fresh email with `team_role=Manager`; recipient accepts the emailed link as a brand-new
user → Active `Buzz Team Membership` created, `Event Manager` role granted, `get_my_teams` includes
the team on their first login.

## Scope

### In
- `user_invitation` hook extension (`extra_invite_params`, `after_accept`)
- `invite_member` wrapper API + pending-invite listing + revoke
- Inviter authorization (Owner/Admin only)

### Out (deferred to)
- Members/invites UI → `01-dashboard/13`
- Attendee-facing invitations (marketing) → future marketing pillar

## Backend changes

### `hooks.py`

```python
user_invitation = {
    "allowed_roles": {"Event Manager": ["Buzz User"], "Buzz User": ["Buzz User"]},
    "extra_invite_params": ["team", "team_role"],
    "after_accept": ["buzz.teams.on_invitation_accepted"],
}
```

### `buzz/teams.py`

- `on_invitation_accepted(invitation, user, user_inserted)` — reads `team` + `team_role` from the
  invitation's extra params; creates Active `Buzz Team Membership` (idempotent: upsert on
  `(team, user)`, re-activate if previously Disabled). Role sync happens via the membership
  controller from step 01.
- Validation at *invite time*, not accept time: the wrapper API checks the inviter.

### `buzz/api/teams.py` additions

- `invite_member(team, email, team_role)` — validates caller has `team_role in {Owner, Admin}` for
  `team`; `team_role` must not be `Owner` (ownership transfer is a separate explicit action);
  delegates to `frappe.core.api.user_invitation.invite_by_email` with
  `extra_params={"team": team, "team_role": team_role}` and `redirect_to_path="/dashboard"`.
- `get_pending_invitations(team)` — Owner/Admin only; pending `User Invitation` rows for the team.
- `revoke_invitation(team, invitation)` — Owner/Admin only.

## Frontend changes

None (UI in `01-dashboard/13`).

## API contract

| Endpoint | Method | Params | Returns | Auth |
|---|---|---|---|---|
| `buzz.api.teams.invite_member` | POST | `team, email, team_role` | `{invitation}` | Owner/Admin of team |
| `buzz.api.teams.get_pending_invitations` | GET | `team` | `[{name, email, team_role, status, creation}]` | Owner/Admin |
| `buzz.api.teams.revoke_invitation` | POST | `team, invitation` | `{ok}` | Owner/Admin |

## Permissions notes

- Inviting grants at most `Admin` — never `Owner`.
- An invited email that already has an account: `after_accept` fires with `user_inserted=False`;
  membership upsert covers both paths.
- Invited existing member: `invite_member` short-circuits with a friendly `frappe.throw`.

## Demo script

1. As alice (Owner of team A): `invite_member(A, "carol@x.com", "Manager")` → invitation email
   (or console link in dev).
2. `get_pending_invitations(A)` → 1 row.
3. Open the accept link in incognito → account created → redirected to `/dashboard`.
4. As carol: `get_my_teams()` → team A with `team_role: Manager`; carol holds `Event Manager`.
5. As bob (non-member): `invite_member(A, ...)` → throws.

## Acceptance criteria (merge gate)

### Automated tests — `buzz/tests/test_team_invitations.py` (new)
`bench --site buzz.localhost run-tests --module buzz.tests.test_team_invitations`
- `invite_member` as Owner creates a pending `User Invitation` with extra params
  `{team, team_role}`.
- `invite_member` as Manager/non-member raises; `team_role="Owner"` raises.
- Accept for a brand-new email: User created, Active membership with invited role,
  `Event Manager`/`Frontdesk Manager` role granted per mapping.
- Accept for an existing user (`user_inserted=False`): membership upserted; previously Disabled
  membership re-activated, not duplicated.
- Inviting an existing Active member throws the friendly error.
- `revoke_invitation` as Admin works; as Manager raises.

### Browser checks (agent-browser)
1. As Owner (console/API) create an invitation; grab the accept URL (dev mode prints it).
2. Fresh browser session → open the accept URL → account/password flow → assert final redirect
   lands on `/dashboard`.
3. Log in as the new user → assert `get_my_teams` (via any team-aware page once
   `01-dashboard/01` exists; until then assert via API response in the browser session) includes
   the team with the invited role.

## Dependencies & risks

- `User Invitation` app-key: invitations are namespaced per app via the hook config — verify the
  accept flow passes `app_name=buzz` end to end on this frappe version.
- Email delivery in dev: dev mode prints the accept URL; demo uses that.
