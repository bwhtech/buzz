import { session } from "@/data/session"
import type { TeamOption, TeamOverview } from "@/types"
import { createResource, useCall } from "frappe-ui"
import { computed, ref, watch } from "vue"

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
	(): TeamOption | null =>
		teams.value.find((team) => team.name === selectedTeamName.value) || null
)

export async function isTeamMember(): Promise<boolean> {
	if (!session.isLoggedIn) return false
	if (!teamsResource.data) await teamsResource.fetch()
	return teams.value.length > 0
}

// Scoped to the selected team rather than to a route, so a switch re-reads whatever
// page is open. v2 path: useCall reads the payload from `data`, which /api/method
// names `message`.
const teamOverview = useCall<TeamOverview, { team: string }>({
	url: "/api/v2/method/buzz.api.teams.get_team_overview",
	params: () => ({ team: selectedTeamName.value }),
	immediate: false,
})

/**
 * The selected team's details, for the pages that show them.
 *
 * The watcher belongs to the caller rather than to this module: at module scope it
 * would fire as soon as get_my_teams settles, putting a request on every manage page
 * instead of the few that read one. Scoped here it also means the page owns its own
 * first fetch, so `loading` is true before the page paints.
 */
export function useTeamOverview() {
	watch(currentTeam, (team) => team && teamOverview.reload(), { immediate: true })
	return teamOverview
}

export function selectTeam(name: string) {
	selectedTeamName.value = name
	localStorage.setItem(STORAGE_KEY, name)
}
