import { ref } from "vue"

// Long enough to read, so a page that loads at once doesn't flash the screen.
const MINIMUM_DURATION = 1000

export const openingTeam = ref<string | null>(null)
let startedAt = 0

export function startOpening(teamName: string) {
	openingTeam.value = teamName
	startedAt = Date.now()
}

export function finishOpening() {
	if (!openingTeam.value) return
	const remaining = MINIMUM_DURATION - (Date.now() - startedAt)
	setTimeout(() => (openingTeam.value = null), Math.max(remaining, 0))
}
