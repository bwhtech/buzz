import { isTeamMember } from "@/data/teams"
import { type Ref, ref } from "vue"

export type TeamAccess = "pending" | "granted" | "denied"

/**
 * Whether the session user belongs to any team.
 *
 * Tri-state so a caller can hold its 404 back until the answer is in, rather than
 * flashing one while the teams load. Shared because pages outside the manager shell
 * need the same guard the shell applies.
 */
export function useTeamAccess(): Ref<TeamAccess> {
	const access = ref<TeamAccess>("pending")

	isTeamMember().then((member) => {
		access.value = member ? "granted" : "denied"
	})

	return access
}
