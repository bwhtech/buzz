import { useLocalStorage } from "@vueuse/core"

export type EventCardLayout = "row" | "cover"

// The same key the public timelines read, so a viewer's choice follows them across both.
export function useEventCardLayout() {
	return useLocalStorage<EventCardLayout>("buzz:event-card-layout", "row")
}
