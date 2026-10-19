import { type Ref, ref } from "vue"

import { hasManageAccess } from "@/data/teams"

export type TeamAccess = "pending" | "granted" | "denied"

/**
 * Whether the session user belongs to any team, or collaborates on an event.
 *
 * Tri-state so a caller can hold its 404 back until the answer is in, rather than
 * flashing one while the teams load.
 */
export function useTeamAccess(): Ref<TeamAccess> {
	const access = ref<TeamAccess>("pending")

	hasManageAccess().then((member) => {
		access.value = member ? "granted" : "denied"
	})

	return access
}
