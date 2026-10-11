<script setup lang="ts">
import { Avatar, Badge, Button, Dialog, ErrorMessage, dayjsLocal, toast, useCall } from "frappe-ui"
import { computed, watch } from "vue"

import DetailRow from "@/components/common/DetailRow.vue"
import type { EventGuest } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ guest: EventGuest | null; payment?: string | null }>()

const open = defineModel<boolean>("open", { required: true })

const emit = defineEmits<{ checkedIn: [ticket: string, at: string] }>()

const name = computed(
	() => props.guest?.attendee_name || props.guest?.attendee_email || "Unnamed guest",
)

const checkedInAt = computed(() =>
	props.guest?.checked_in_at ? dayjsLocal(props.guest.checked_in_at).format("h:mm A") : null,
)

const registeredAt = computed(() =>
	props.guest?.registered_at
		? dayjsLocal(props.guest.registered_at).format("D MMM YYYY, h:mm A")
		: null,
)

interface CheckInResponse {
	message: string
	ticket: { id: string; check_in_time: string }
}

const checkIn = useCall<CheckInResponse, { ticket_id: string }>({
	url: "/api/v2/method/buzz.api.checkin.checkin_ticket",
	method: "POST",
	immediate: false,
	onSuccess: (data) => {
		emit("checkedIn", data.ticket.id, data.ticket.check_in_time)
		toast.success(data.message)
		open.value = false
	},
})

// The next guest opens clean, without the last one's error.
watch(
	() => props.guest?.name,
	() => checkIn.reset(),
)
</script>

<template>
	<Dialog v-model:open="open" size="md" :show-close-button="false">
		<template #title>
			<div class="flex items-center gap-3">
				<Avatar :label="name" size="2xl" />
				<div class="min-w-0 flex-1">
					<p class="truncate text-lg font-semibold text-ink-gray-9">{{ name }}</p>
					<p v-if="guest?.attendee_email" class="truncate text-base font-normal text-ink-gray-5">
						{{ guest.attendee_email }}
					</p>
				</div>
				<Badge
					v-if="checkedInAt"
					theme="green"
					variant="subtle"
					size="lg"
					:label="`Checked in · ${checkedInAt}`"
				/>
				<Badge v-else variant="subtle" size="lg" label="Not checked in" />
			</div>
		</template>

		<div v-if="guest" class="space-y-5">
			<!-- The tier is what the desk acts on, so it reads at a glance rather than as a row. -->
			<div class="space-y-1.5">
				<p class="text-sm font-medium text-ink-gray-7">Ticket</p>
				<p class="rounded-7 bg-surface-gray-2 px-3 py-2.5 text-lg font-medium text-ink-gray-9">
					{{ guest.ticket_type || "—" }}
				</p>
			</div>

			<dl class="space-y-2 text-base">
				<DetailRow
					v-for="addOn in guest.add_ons"
					:key="addOn.title"
					:label="addOn.title"
					:value="addOn.value || 'Yes'"
				/>
				<DetailRow v-if="registeredAt" label="Registered" :value="registeredAt" />
				<DetailRow v-if="payment" label="Paid" :value="payment" />
			</dl>

			<ErrorMessage :message="serverErrorMessage(checkIn.error)" />
		</div>

		<template #actions="{ close }">
			<div class="flex gap-2">
				<Button
					variant="solid"
					theme="green"
					size="lg"
					class="flex-1 transition-transform duration-150 ease-out active:scale-[0.97] motion-reduce:transition-none"
					:label="checkedInAt ? `Checked in at ${checkedInAt}` : 'Check in'"
					:disabled="Boolean(checkedInAt)"
					:loading="checkIn.loading"
					@click="guest && checkIn.submit({ ticket_id: guest.name })"
				/>
				<Button size="lg" label="Close" @click="close" />
			</div>
		</template>
	</Dialog>
</template>
