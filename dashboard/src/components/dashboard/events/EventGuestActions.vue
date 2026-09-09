<script setup lang="ts">
import { call, toast } from "frappe-ui"
import { computed, ref } from "vue"

import GuestRegistrationDialog from "@/components/dashboard/events/GuestRegistrationDialog.vue"
import QuickActionsRail, {
	type QuickAction,
} from "@/components/dashboard/events/QuickActionsRail.vue"
import QuickActionTile from "@/components/dashboard/events/QuickActionTile.vue"
import RegistrationDialog from "@/components/dashboard/events/RegistrationDialog.vue"
import type { EventGuest, EventGuests } from "@/types"
import { downloadCsv } from "@/utils/csv"

const props = defineProps<{
	event: string
	closed: boolean
	canWrite: boolean
	title?: string | null
	registrationLink?: string | null
	allowGuestBooking: boolean
	guestVerificationMethod: string
	// What the list is currently showing, so the export is the same list.
	query: { search: string; ticket_types: string; order: string }
}>()
const emit = defineEmits<{ changed: [] }>()

const dialogOpen = ref(false)
const guestDialogOpen = ref(false)
const exporting = ref(false)

const VERIFICATION_LABELS: Record<string, string> = {
	"Email OTP": "Email verification",
	"Phone OTP": "Phone verification",
}

const guestSubtitle = computed(() => {
	if (!props.allowGuestBooking) return "Disabled"
	const verification = VERIFICATION_LABELS[props.guestVerificationMethod]
	return verification ? `Enabled · ${verification}` : "Enabled"
})

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

// The rows differ only in icon, label and what they do, so they are data rather than
// two near-identical buttons. A link row renders as an anchor; the rest as buttons.
const actions = computed<QuickAction[]>(() =>
	[
		props.registrationLink
			? {
					icon: "lucide-arrow-up-right",
					label: "Registration page",
					link: props.registrationLink,
				}
			: null,
		{
			icon: "lucide-download",
			label: "Download CSV",
			loading: exporting.value,
			onClick: exportGuests,
		},
	].filter((action) => action !== null),
)
</script>

<template>
	<QuickActionsRail
		subject="Registration"
		open-icon="lucide-ticket"
		closed-icon="lucide-ticket-x"
		:closed="closed"
		:can-write="canWrite"
		:actions="actions"
		@toggle="dialogOpen = true"
	>
		<QuickActionTile
			icon="lucide-hat-glasses"
			title="Guest registration"
			:subtitle="guestSubtitle"
			:tone="allowGuestBooking ? 'violet' : 'gray'"
			:disabled="!canWrite"
			@click="guestDialogOpen = true"
		/>
	</QuickActionsRail>

	<RegistrationDialog
		v-model="dialogOpen"
		:event="event"
		:closed="closed"
		@changed="emit('changed')"
	/>

	<GuestRegistrationDialog
		v-model="guestDialogOpen"
		:event="event"
		:enabled="allowGuestBooking"
		:method="guestVerificationMethod"
		@changed="emit('changed')"
	/>
</template>
