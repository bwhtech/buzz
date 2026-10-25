<script setup lang="ts">
import { Badge, Button, Checkbox, dayjsLocal } from "frappe-ui"

import type { PendingBooking } from "@/types"

defineProps<{ booking: PendingBooking; selected: boolean; busy: boolean }>()
const emit = defineEmits<{ toggle: []; approve: []; decline: [] }>()
</script>

<template>
	<li class="flex items-start gap-3 px-3.5 py-3">
		<Checkbox
			class="mt-1"
			:model-value="selected"
			:aria-label="`Select ${booking.buyer_name}`"
			@update:model-value="emit('toggle')"
		/>

		<div class="min-w-0 flex-1 space-y-1.5">
			<div class="flex flex-wrap items-baseline gap-x-2">
				<span class="truncate text-base font-medium text-ink-gray-9">{{ booking.buyer_name }}</span>
				<span class="truncate text-base text-ink-gray-5">{{ booking.buyer_email }}</span>
				<Badge
					v-if="booking.previously_declined"
					theme="red"
					variant="subtle"
					label="Previously declined"
				/>
			</div>

			<ul class="space-y-0.5 text-sm text-ink-gray-7">
				<li
					v-for="(attendee, index) in booking.attendees"
					:key="index"
					class="flex flex-wrap gap-x-2"
				>
					<span>{{ attendee.full_name }}</span>
					<span v-if="attendee.email" class="text-ink-gray-5">{{ attendee.email }}</span>
					<Badge variant="subtle" :label="attendee.ticket_type" />
				</li>
			</ul>

			<dl v-if="booking.answers.length" class="space-y-0.5 text-sm">
				<div v-for="answer in booking.answers" :key="answer.label" class="flex gap-2">
					<dt class="text-ink-gray-5">{{ answer.label }}</dt>
					<dd class="text-ink-gray-8">{{ answer.value }}</dd>
				</div>
			</dl>

			<p class="text-sm text-ink-gray-5">
				Requested {{ dayjsLocal(booking.requested_at).format("D MMM, h:mm A") }}
			</p>
		</div>

		<div class="flex shrink-0 gap-1.5">
			<Button
				theme="red"
				variant="subtle"
				label="Decline"
				:disabled="busy"
				@click="emit('decline')"
			/>
			<Button
				theme="green"
				variant="subtle"
				label="Approve"
				:disabled="busy"
				@click="emit('approve')"
			/>
		</div>
	</li>
</template>
