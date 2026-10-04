// Mirrors WRITE_ROLES in buzz/permissions.py, which is what the server actually enforces.
const EVENT_WRITE_ROLES = ["Owner", "Admin", "Manager"]

/** Whether a team role may create events. Used to gate the form, not to secure it. */
export function canCreateEvents(teamRole: string | undefined): boolean {
	return Boolean(teamRole && EVENT_WRITE_ROLES.includes(teamRole))
}

// Mirrors ADMIN_ROLES in buzz/permissions.py; can_manage_members is the server's check.
const MEMBER_WRITE_ROLES = ["Owner", "Admin"]

/** Whether a team role may invite and remove members. Gates the UI, not the API. */
export function canManageMembers(teamRole: string | undefined): boolean {
	return Boolean(teamRole && MEMBER_WRITE_ROLES.includes(teamRole))
}

// Mirrors the membership doctype's Select options, minus Owner. The server rejects anything
// outside this set, so a drift here fails loudly rather than silently.
export const ASSIGNABLE_TEAM_ROLES = ["Admin", "Manager", "Frontdesk", "Viewer"]

// Most authority first, which is the order the roster lists people in.
const TEAM_ROLE_ORDER = ["Owner", ...ASSIGNABLE_TEAM_ROLES]

/** Where a role sits in the roster. An unknown role sorts last rather than first. */
export function teamRoleRank(teamRole: string): number {
	const rank = TEAM_ROLE_ORDER.indexOf(teamRole)
	return rank === -1 ? TEAM_ROLE_ORDER.length : rank
}
