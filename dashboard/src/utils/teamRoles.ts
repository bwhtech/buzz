// Mirrors WRITE_ROLES in buzz/permissions.py, which is what the server actually enforces.
const EVENT_WRITE_ROLES = ["Owner", "Admin", "Manager"]

/** Whether a team role may create events. Used to gate the form, not to secure it. */
export function canCreateEvents(teamRole: string | undefined): boolean {
	return Boolean(teamRole && EVENT_WRITE_ROLES.includes(teamRole))
}
