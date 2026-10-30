import { useLocalStorage } from "@vueuse/core"
import { type Ref, computed } from "vue"

import type { GuestZone } from "@/types"

export const ANY_ZONE = "any"

/** The zone this device checks guests into, remembered per event. */
export function useCheckInZone(event: string, zones: Ref<GuestZone[]>) {
	const stored = useLocalStorage(`buzz:checkin-zone:${event}`, "")

	const selected = computed<string>({
		get() {
			// With one zone the picker is hidden, so a stored "Any zone" would be stuck.
			if (zones.value.length < 2) return zones.value[0]?.name ?? ""
			const known =
				stored.value === ANY_ZONE || zones.value.some((zone) => zone.name === stored.value)
			return known ? stored.value : zones.value[0].name
		},
		set: (value) => (stored.value = value),
	})

	return {
		selected,
		// What the API is sent: nothing in "Any zone" mode.
		zone: computed(() => (selected.value === ANY_ZONE ? "" : selected.value)),
		defaultZone: computed(() => zones.value[0]?.name ?? ""),
	}
}
