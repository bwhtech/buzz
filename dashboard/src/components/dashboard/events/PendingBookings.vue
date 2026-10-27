<script setup lang="ts">
import { Button, Tooltip, toast } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import DeclineBookingsDialog from "@/components/dashboard/events/DeclineBookingsDialog.vue"
import EventGuestItem from "@/components/dashboard/events/EventGuestItem.vue"
import GuestInfoDrawer from "@/components/dashboard/events/GuestInfoDrawer.vue"
import { useApproveBookings, useDeclineBookings } from "@/data/approvals"
import type { EventGuest, PendingBooking, PendingBookings } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ event: string; pending: PendingBookings | null; error?: string }>()
const emit = defineEmits<{ changed: [] }>()

const bookings = computed(() => props.pending?.bookings ?? [])

const approval = useApproveBookings()
const decline = useDeclineBookings()
const busy = computed(() => approval.loading || decline.loading)

// A request has no ticket yet, so the buyer stands in as the guest the row and drawer show.
function asGuest(booking: PendingBooking): EventGuest {
	return {
		name: booking.name,
		attendee_name: booking.buyer_name,
		attendee_email: booking.buyer_email,
		ticket_type: booking.attendees[0]?.ticket_type ?? null,
		registered_at: booking.requested_at,
		add_ons: [],
		zones: [],
	}
}

const selectedName = ref<string | null>(null)
const selectedIndex = computed(() =>
	bookings.value.findIndex((booking) => booking.name === selectedName.value),
)
const selectedRequest = computed(() => bookings.value[selectedIndex.value] ?? null)

const drawerOpen = computed<boolean>({
	get: () => selectedRequest.value !== null,
	set: (open) => !open && (selectedName.value = null),
})

const step = (by: number) => {
	const next = bookings.value[selectedIndex.value + by]
	if (next) selectedName.value = next.name
}

const declineTarget = ref<string[]>([])
const declineOpen = ref(false)

async function approve(names: string[]) {
	try {
		const result = await approval.submit({ event: props.event, bookings: names })
		if (result?.approved.length) toast.success(`${result.approved.length} approved`)
		result?.failed.forEach(({ booking, error }) => toast.error(`${booking}: ${error}`))
		selectedName.value = null
	} catch (error) {
		toast.error(serverErrorMessage(error))
	}
	emit("changed")
}

function askToDecline(names: string[]) {
	declineTarget.value = names
	declineOpen.value = true
}

async function confirmDecline(message: string) {
	try {
		const result = await decline.submit({
			event: props.event,
			bookings: declineTarget.value,
			message: message.trim() || null,
		})
		toast.success(`${result?.declined.length ?? 0} declined`)
		declineOpen.value = false
		selectedName.value = null
	} catch (error) {
		toast.error(serverErrorMessage(error))
	}
	emit("changed")
}
</script>

<template>
	<ul
		v-if="bookings.length"
		class="divide-y divide-outline-gray-1 overflow-hidden rounded-5 border border-outline-gray-2"
	>
		<EventGuestItem
			v-for="booking in bookings"
			:key="booking.name"
			:guest="asGuest(booking)"
			:selected="booking.name === selectedName"
			@open="selectedName = booking.name"
		>
			<template #actions>
				<Tooltip text="Approve">
					<Button
						variant="subtle"
						theme="green"
						icon="lucide-check"
						aria-label="Approve"
						:disabled="busy"
						@click="approve([booking.name])"
					/>
				</Tooltip>
				<Tooltip text="Decline">
					<Button
						variant="subtle"
						theme="red"
						icon="lucide-x"
						aria-label="Decline"
						:disabled="busy"
						@click="askToDecline([booking.name])"
					/>
				</Tooltip>
			</template>
		</EventGuestItem>
	</ul>
	<EmptyState
		v-else
		title="No requests waiting"
		description="Requests to join show up here for you to approve or decline."
		icon="lucide-user-check"
	/>

	<GuestInfoDrawer
		v-model:open="drawerOpen"
		:guest="selectedRequest && asGuest(selectedRequest)"
		:request="selectedRequest"
		:event="null"
		:has-previous="selectedIndex > 0"
		:has-next="selectedIndex >= 0 && selectedIndex < bookings.length - 1"
		@previous="step(-1)"
		@next="step(1)"
		@approve="approve([selectedRequest!.name])"
		@decline="askToDecline([selectedRequest!.name])"
	/>

	<DeclineBookingsDialog
		v-model="declineOpen"
		:count="declineTarget.length"
		:loading="decline.loading"
		@confirm="confirmDecline"
	/>
</template>
