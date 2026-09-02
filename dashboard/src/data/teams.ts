import { createResource } from "frappe-ui"
import { computed, ref } from "vue"

import { session } from "@/data/session"
import type { TeamOption } from "@/types"

const STORAGE_KEY = "buzz:current-team"

const selectedTeamName = ref(localStorage.getItem(STORAGE_KEY) || "")

const teamsResource = createResource<TeamOption[]>({
	url: "buzz.api.teams.get_my_teams",
	cache: "My Teams",
	// Not `auto`: get_my_teams is not allow_guest, so a logged-out visitor on a public
	// booking route would fire a 403 on module load.
	onSuccess(myTeams: TeamOption[]) {
		// A revoked membership leaves the stored name pointing at nothing.
		if (!myTeams.some((team) => team.name === selectedTeamName.value)) {
			selectTeam(myTeams[0]?.name || "")
		}
	},
})

export const teams = computed((): TeamOption[] => teamsResource.data || [])

export const currentTeam = computed(
	(): TeamOption | null => teams.value.find((team) => team.name === selectedTeamName.value) || null,
)

export async function isTeamMember(): Promise<boolean> {
	if (!session.isLoggedIn) return false
	if (!teamsResource.data) await teamsResource.fetch()
	return teams.value.length > 0
}

export function selectTeam(name: string) {
	selectedTeamName.value = name
	localStorage.setItem(STORAGE_KEY, name)
}
