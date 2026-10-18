<script setup lang="ts">
import { Avatar, Button } from "frappe-ui"
import { ref } from "vue"

defineProps<{
	tickets: {
		name: string
		attendee_name: string
		attendee_email: string | null
		ticket_type: string
		qr_code: string | null
	}[]
	downloadUrl: string
}>()

const openTicket = ref(-1)

function toggle(index: number) {
	openTicket.value = openTicket.value === index ? -1 : index
}
</script>

<template>
	<section class="flex flex-col gap-3">
		<div class="flex items-center justify-between gap-3">
			<h2 class="flex items-center gap-2 text-base-semibold text-ink-gray-9">
				{{ __("Your tickets") }}
				<span class="font-normal tabular-nums text-ink-gray-5">{{ tickets.length }}</span>
			</h2>
			<Button
				variant="ghost"
				icon-left="lucide-download"
				:label="__('Download all')"
				:href="downloadUrl"
			/>
		</div>

		<div class="overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-base">
			<div
				v-for="(ticket, index) in tickets"
				:key="ticket.name"
				:class="{ 'border-t border-outline-gray-1': index }"
			>
				<div class="flex items-center gap-3 px-3.5 py-3">
					<Avatar :label="ticket.attendee_name" size="lg" />
					<div class="flex min-w-0 flex-1 flex-col gap-0.5">
						<span class="truncate text-base-medium text-ink-gray-9">{{
							ticket.attendee_name
						}}</span>
						<span class="truncate text-p-sm text-ink-gray-5">
							{{ ticket.ticket_type }} · {{ ticket.name }}
						</span>
					</div>
					<Button
						variant="subtle"
						icon-left="lucide-qr-code"
						:label="openTicket === index ? __('Hide') : __('Show QR')"
						:aria-expanded="openTicket === index"
						@click="toggle(index)"
					/>
				</div>
				<div
					v-if="openTicket === index"
					class="qr-panel flex flex-col items-center gap-2.5 px-3.5 pb-5 pt-1"
				>
					<img
						v-if="ticket.qr_code"
						:src="ticket.qr_code"
						:alt="__('QR code for {0}', [ticket.attendee_name])"
						class="size-[188px] rounded-5 border border-outline-gray-1 bg-white p-2.5"
					/>
					<span v-if="ticket.attendee_email" class="text-p-xs text-ink-gray-5">
						{{ ticket.attendee_email }}
					</span>
				</div>
			</div>
		</div>
	</section>
</template>

<style scoped>
.qr-panel {
	animation: fade-up-in 240ms cubic-bezier(0.23, 1, 0.32, 1) both;
}

@media (prefers-reduced-motion: reduce) {
	.qr-panel {
		animation: none;
	}
}
</style>
