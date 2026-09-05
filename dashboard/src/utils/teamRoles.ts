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
