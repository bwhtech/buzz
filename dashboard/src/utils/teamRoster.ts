import type { TeamInvite, TeamMember, TeamOverview } from "@/types"

/** One line of the roster: a member, or an invitation still waiting on its recipient. */
export interface RosterRow {
	key: string
	name: string
	email: string
	role: string
	image?: string
	member?: TeamMember
}

/**
 * Members and pending invitations as one list, so the roster reads as the whole team,
 * with the people who have not accepted yet at the bottom.
 */
export function rosterRows(team: Pick<TeamOverview, "members" | "invites">): RosterRow[] {
	return [...team.members.map(memberRow), ...team.invites.map(inviteRow)]
}

/** Whether a row answers a search, matched against everything the row shows. */
export function matchesQuery(row: RosterRow, query: string): boolean {
	return [row.name, row.email, row.role].some((field) => field.toLowerCase().includes(query))
}

function memberRow(member: TeamMember): RosterRow {
	return {
		key: member.user,
		name: member.full_name ?? member.user,
		email: member.user,
		role: member.team_role,
		image: member.user_image ?? undefined,
		member,
	}
}

// There is no user yet, so no name and no image — the address stands in for both.
function inviteRow(invite: TeamInvite): RosterRow {
	return {
		key: `invite:${invite.email}`,
		name: invite.email,
		email: invite.email,
		role: invite.team_role,
	}
}
