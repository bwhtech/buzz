import type { TeamOption } from "@/types"
import { createResource } from "frappe-ui"
import { computed, ref } from "vue"

const STORAGE_KEY = "buzz:current-team"

const selectedTeamName = ref(localStorage.getItem(STORAGE_KEY) || "")

const teamsResource = createResource<TeamOption[]>({
	url: "buzz.api.teams.get_my_teams",
	cache: "My Teams",
	auto: true,
	onSuccess(myTeams: TeamOption[]) {
		// A revoked membership leaves the stored name pointing at nothing.
		if (!myTeams.some((team) => team.name === selectedTeamName.value)) {
			selectTeam(myTeams[0]?.name || "")
		}
	},
})

export const teams = computed((): TeamOption[] => teamsResource.data || [])

export const currentTeam = computed(
	(): TeamOption | null =>
		teams.value.find((team) => team.name === selectedTeamName.value) || null
)

export function selectTeam(name: string) {
	selectedTeamName.value = name
	localStorage.setItem(STORAGE_KEY, name)
}
