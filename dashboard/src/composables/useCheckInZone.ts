import { useLocalStorage } from "@vueuse/core"
import { useCall } from "frappe-ui"
import { type Ref, computed, ref } from "vue"

import type { GuestZone, ZoneStatus } from "@/types"

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
		isAnyZone: computed(() => selected.value === ANY_ZONE),
		// What the API is sent: nothing in "Any zone" mode.
		zone: computed(() => (selected.value === ANY_ZONE ? "" : selected.value)),
		defaultZone: computed(() => zones.value[0]?.name ?? ""),
	}
}

/** Per-zone entry status of the open guest, read without the zone rules of a scan. */
export function useZoneStatuses() {
	const statuses = ref<ZoneStatus[]>([])

	const openTicket = ref("")

	const call = useCall<{ ticket: { id: string }; zones: ZoneStatus[] }, { ticket_id: string }>({
		url: "/api/v2/method/buzz.api.checkin.validate_ticket_for_checkin",
		method: "POST",
		immediate: false,
		// A late answer for the previous guest must not land on the next one.
		onSuccess: (data) => {
			if (data.ticket.id === openTicket.value) statuses.value = data.zones
		},
	})

	const load = (ticket: string) => {
		openTicket.value = ticket
		statuses.value = []
		call.submit({ ticket_id: ticket })
	}

	return { statuses, load }
}
