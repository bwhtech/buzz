<script setup lang="ts">
import { Button, Tooltip, toast } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import DeclineBookingsDialog from "@/components/dashboard/events/DeclineBookingsDialog.vue"
import EventGuestItem from "@/components/dashboard/events/EventGuestItem.vue"
import GuestInfoDrawer from "@/components/dashboard/events/GuestInfoDrawer.vue"
import { useApproveRequest, useDeclineRequest } from "@/data/requests"
import type { EventGuest, RegistrationRequest, RequestStatus } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ requests: RegistrationRequest[] }>()
const emit = defineEmits<{ changed: [confirmed: boolean] }>()

const STATUS_BADGES: Record<RequestStatus, { label: string; theme: "blue" | "gray" | "amber" }> = {
	Requested: { label: "Approval", theme: "blue" },
	Waitlisted: { label: "Waitlist", theme: "gray" },
	"Payment Pending": { label: "Payment pending", theme: "amber" },
}

const approval = useApproveRequest()
const decline = useDeclineRequest()
const busy = computed(() => approval.loading || decline.loading)

// A request has no ticket yet, so the buyer stands in as the guest the row and drawer show.
function asGuest(request: RegistrationRequest): EventGuest {
	return {
		name: request.name,
		attendee_name: request.buyer_name,
		attendee_email: request.buyer_email,
		ticket_type: request.attendees[0]?.ticket_type ?? null,
		registered_at: request.requested_at,
		add_ons: [],
		zones: [],
	}
}

const isOpen = (request: RegistrationRequest) => request.status !== "Payment Pending"

const selectedName = ref<string | null>(null)
const selectedIndex = computed(() =>
	props.requests.findIndex((request) => request.name === selectedName.value),
)
const selectedRequest = computed(() => props.requests[selectedIndex.value] ?? null)

const drawerOpen = computed<boolean>({
	get: () => selectedRequest.value !== null,
	set: (open) => !open && (selectedName.value = null),
})

const step = (by: number) => {
	const next = props.requests[selectedIndex.value + by]
	if (next) selectedName.value = next.name
}

const declineTarget = ref("")
const declineOpen = ref(false)

async function approve(booking: string) {
	try {
		await approval.submit({ booking })
		toast.success("Request approved")
		selectedName.value = null
		emit("changed", true)
	} catch (error) {
		toast.error(serverErrorMessage(error))
	}
}

function askToDecline(booking: string) {
	declineTarget.value = booking
	declineOpen.value = true
}

async function confirmDecline(message: string) {
	try {
		await decline.submit({ booking: declineTarget.value, message: message.trim() || undefined })
		toast.success("Request declined")
		declineOpen.value = false
		selectedName.value = null
		emit("changed", false)
	} catch (error) {
		toast.error(serverErrorMessage(error))
	}
}
</script>

<template>
	<ul
		v-if="requests.length"
		class="divide-y divide-outline-gray-1 overflow-hidden rounded-5 border border-outline-gray-2"
	>
		<EventGuestItem
			v-for="request in requests"
			:key="request.name"
			:guest="asGuest(request)"
			:status="STATUS_BADGES[request.status]"
			:selected="request.name === selectedName"
			@open="selectedName = request.name"
		>
			<template v-if="isOpen(request)" #actions>
				<Tooltip text="Approve">
					<Button
						variant="subtle"
						theme="green"
						icon="lucide-check"
						aria-label="Approve"
						:disabled="busy"
						@click="approve(request.name)"
					/>
				</Tooltip>
				<Tooltip text="Decline">
					<Button
						variant="subtle"
						theme="red"
						icon="lucide-x"
						aria-label="Decline"
						:disabled="busy"
						@click="askToDecline(request.name)"
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
		:has-next="selectedIndex >= 0 && selectedIndex < requests.length - 1"
		@previous="step(-1)"
		@next="step(1)"
		@approve="approve(selectedRequest!.name)"
		@decline="askToDecline(selectedRequest!.name)"
	/>

	<DeclineBookingsDialog
		v-model="declineOpen"
		:loading="decline.loading"
		@confirm="confirmDecline"
	/>
</template>
