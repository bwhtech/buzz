import { useDoctype, useList } from "frappe-ui"
import { ref } from "vue"

export interface Venue {
	name: string
	address: string
}

const team = ref("")

// Plain doctype reads and writes, so they go through the document API rather than a buzz
// endpoint. Event Venue carries the team query condition and permission hooks, so the
// team filter below narrows what the picker asks for — it is not what enforces scope.
export const venues = useList<Venue>({
	doctype: "Event Venue",
	filters: () => ({ team: team.value }),
	fields: ["name", "address"],
	orderBy: "modified desc",
	// One page holds every venue a team has; the picker does not page.
	limit: 1000,
	immediate: false,
	refetch: false,
})

export function loadVenues(name: string) {
	team.value = name
	return venues.reload()
}

// Event Venue is autonamed by prompt, so the `name` sent is the venue's own.
export const createVenue = useDoctype<Venue & { team: string }>("Event Venue").insert
