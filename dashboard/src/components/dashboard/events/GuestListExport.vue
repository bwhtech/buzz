<script setup lang="ts">
import { Button, call, toast } from "frappe-ui"
import { ref } from "vue"

import { PRESSABLE } from "@/components/dashboard/events/QuickActionTile.vue"
import type { EventGuest, EventGuests } from "@/types"
import { downloadCsv } from "@/utils/csv"

const props = defineProps<{
	event: string
	title?: string | null
	// What the list is currently showing, so the export is the same list.
	query: { search: string; filters: string; order: string }
}>()

const exporting = ref(false)

// The list is paged, so the export walks it: a hundred at a time until the server says
// there is no next page.
async function fetchAll(): Promise<EventGuest[]> {
	const all: EventGuest[] = []
	for (let start = 0; ; start += 100) {
		const page: EventGuests = await call("buzz.api.events.get_event_guests", {
			event: props.event,
			...props.query,
			start,
			limit: 100,
		})
		all.push(...page.guests)
		if (!page.has_next_page) return all
	}
}

async function exportGuests() {
	exporting.value = true
	try {
		const guests = await fetchAll()
		downloadCsv(`${props.title || "guests"}.csv`, [
			["Name", "Email", "Ticket type", "Registered at"],
			...guests.map((guest) => [
				guest.attendee_name,
				guest.attendee_email,
				guest.ticket_type,
				guest.registered_at,
			]),
		])
	} catch {
		toast.error("Could not export the guest list. Try again.")
	} finally {
		exporting.value = false
	}
}
</script>

<template>
	<h3 class="text-p-sm font-medium text-ink-gray-5">Quick actions</h3>
	<Button
		:class="`w-full !justify-start ${PRESSABLE}`"
		variant="ghost"
		label="Download CSV"
		:loading="exporting"
		@click="exportGuests"
	>
		<template #prefix>
			<span class="lucide-download size-4" aria-hidden="true" />
		</template>
	</Button>
</template>
