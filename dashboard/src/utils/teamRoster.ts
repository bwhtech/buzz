import type { TeamInvite, TeamMember, TeamOverview } from "@/types"

import { teamRoleRank } from "./teamRoles.ts"

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
 * with the people who have not accepted yet at the bottom. Each group runs from the most
 * authority to the least, and alphabetically inside a role.
 */
export function rosterRows(team: Pick<TeamOverview, "members" | "invites">): RosterRow[] {
	return [...byRole(team.members.map(memberRow)), ...byRole(team.invites.map(inviteRow))]
}

function byRole(rows: RosterRow[]): RosterRow[] {
	return rows.toSorted(
		(one, other) =>
			teamRoleRank(one.role) - teamRoleRank(other.role) || one.name.localeCompare(other.name),
	)
}

/** Whether a row answers a search, matched against everything the row shows. */
export function matchesQuery(row: RosterRow, loweredQuery: string): boolean {
	return [row.name, row.email, row.role].some((field) => field.toLowerCase().includes(loweredQuery))
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
