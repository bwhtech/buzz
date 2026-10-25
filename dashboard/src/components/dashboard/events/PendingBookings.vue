<script setup lang="ts">
import { Button, Checkbox, toast } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import DeclineBookingsDialog from "@/components/dashboard/events/DeclineBookingsDialog.vue"
import PendingBookingItem from "@/components/dashboard/events/PendingBookingItem.vue"
import { useRowSelection } from "@/composables/useRowSelection"
import { useApproveBookings, useDeclineBookings } from "@/data/approvals"
import type { PendingBookings } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ event: string; pending: PendingBookings | null; error?: string }>()
const emit = defineEmits<{ changed: [] }>()

const bookings = computed(() => props.pending?.bookings ?? [])
const selection = useRowSelection(computed(() => bookings.value.map((booking) => booking.name)))
const allSelected = computed(
	() => bookings.value.length > 0 && selection.selected.value.length === bookings.value.length,
)

const approval = useApproveBookings()
const decline = useDeclineBookings()
const busy = computed(() => approval.loading || decline.loading)

// The names a button acts on: one row, or the ticked rows.
const target = ref<string[]>([])
const declineOpen = ref(false)

function toggleAll() {
	bookings.value.forEach((booking) => {
		if (allSelected.value === selection.isSelected(booking.name)) selection.toggle(booking.name)
	})
}

async function approve(names: string[]) {
	try {
		const result = await approval.submit({ event: props.event, bookings: names })
		if (result?.approved.length) toast.success(`${result.approved.length} approved`)
		result?.failed.forEach(({ booking, error }) => toast.error(`${booking}: ${error}`))
	} catch (error) {
		toast.error(serverErrorMessage(error))
	}
	finish()
}

function askToDecline(names: string[]) {
	target.value = names
	declineOpen.value = true
}

async function confirmDecline(message: string) {
	try {
		const result = await decline.submit({
			event: props.event,
			bookings: target.value,
			message: message.trim() || null,
		})
		toast.success(`${result?.declined.length ?? 0} declined`)
		declineOpen.value = false
	} catch (error) {
		toast.error(serverErrorMessage(error))
	}
	finish()
}

function finish() {
	selection.clear()
	emit("changed")
}
</script>

<template>
	<section class="space-y-3">
		<div v-if="bookings.length" class="flex min-h-8 items-center gap-3 px-3.5">
			<Checkbox :model-value="allSelected" label="Select all" @update:model-value="toggleAll" />
			<template v-if="selection.selected.value.length">
				<span class="text-sm text-ink-gray-5">{{ selection.selected.value.length }} selected</span>
				<Button
					size="sm"
					theme="green"
					variant="subtle"
					label="Approve"
					:disabled="busy"
					@click="approve(selection.selected.value)"
				/>
				<Button
					size="sm"
					theme="red"
					variant="subtle"
					label="Decline"
					:disabled="busy"
					@click="askToDecline(selection.selected.value)"
				/>
			</template>
		</div>

		<ul
			v-if="bookings.length"
			class="divide-y divide-outline-gray-1 overflow-hidden rounded-5 border border-outline-gray-2"
		>
			<PendingBookingItem
				v-for="booking in bookings"
				:key="booking.name"
				:booking="booking"
				:selected="selection.isSelected(booking.name)"
				:busy="busy"
				@toggle="selection.toggle(booking.name)"
				@approve="approve([booking.name])"
				@decline="askToDecline([booking.name])"
			/>
		</ul>
		<EmptyState
			v-else
			title="No requests waiting"
			description="Requests to join show up here for you to approve or decline."
			icon="lucide-user-check"
		/>
	</section>

	<DeclineBookingsDialog
		v-model="declineOpen"
		:count="target.length"
		:loading="decline.loading"
		@confirm="confirmDecline"
	/>
</template>
