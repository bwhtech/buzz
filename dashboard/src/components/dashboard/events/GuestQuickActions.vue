<script setup lang="ts">
import { Button, call, toast } from "frappe-ui"
import { ref } from "vue"
import { useRouter } from "vue-router"

import QuickActionTile, { PRESSABLE } from "@/components/dashboard/events/QuickActionTile.vue"
import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import type { EventGuest, EventGuests } from "@/types"
import { downloadCsv } from "@/utils/csv"

const props = defineProps<{
	event: string
	title?: string | null
	// What the list is currently showing, so the export is the same list.
	query: { search: string; filters: string; order: string; zone: string }
	checkedIn: number
	total: number
}>()

const exporting = ref(false)
const router = useRouter()

const copyToClipboard = useCopyToClipboard()

const checkInHref = () =>
	router.resolve({ name: "check-in", params: { eventName: props.event } }).href

const openCheckIn = () => window.open(checkInHref(), "_blank")

const copyCheckInLink = () =>
	copyToClipboard(new URL(checkInHref(), window.location.origin).href, "Check-in link copied")

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

const actions = [
	{ label: "Copy check-in link", icon: "lucide-link", run: copyCheckInLink },
	{
		label: "Manage zones",
		icon: "lucide-settings-2",
		run: () => router.push({ name: "event-settings", params: { eventId: props.event } }),
	},
	{ label: "Download CSV", icon: "lucide-download", run: exportGuests },
]
</script>

<template>
	<h3 class="text-p-sm font-medium text-ink-gray-5">Quick actions</h3>
	<QuickActionTile
		icon="lucide-scan-line"
		title="Check-in"
		:subtitle="`${checkedIn} of ${total} checked in`"
		tone="green"
		@click="openCheckIn"
	/>
	<section>
		<Button
			v-for="action in actions"
			:key="action.label"
			:class="`w-full !justify-start ${PRESSABLE}`"
			variant="ghost"
			:label="action.label"
			:loading="action.label === 'Download CSV' && exporting"
			@click="action.run"
		>
			<template #prefix>
				<span class="size-4" :class="action.icon" aria-hidden="true" />
			</template>
		</Button>
	</section>
</template>
