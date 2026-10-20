import type { TeamOption } from "@/types"

import { canCreateEvents } from "./teamRoles.ts"

/** The "Personal" choice before the user's personal team exists; choosing it creates one. */
export const NEW_PERSONAL_TEAM = "new-personal-team"

type SelectableTeam = Pick<TeamOption, "name" | "team_name" | "team_role" | "is_personal">

/** Who a new event can be hosted as: the user's personal team first, then their teams. */
export function eventTeamOptions(
	teams: SelectableTeam[],
	{ personalTeamsEnabled, personalLabel }: { personalTeamsEnabled: boolean; personalLabel: string },
) {
	const options = teams
		.filter((team) => canCreateEvents(team.team_role))
		.toSorted((a, b) => Number(b.is_personal) - Number(a.is_personal))
		.map((team) => ({ value: team.name, label: team.is_personal ? personalLabel : team.team_name }))
	const hasPersonal = teams.some((team) => team.is_personal)
	return personalTeamsEnabled && !hasPersonal
		? [{ value: NEW_PERSONAL_TEAM, label: personalLabel }, ...options]
		: options
}
