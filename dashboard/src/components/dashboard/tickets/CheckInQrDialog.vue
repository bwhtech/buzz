<script setup lang="ts">
import { Badge, Dialog } from "frappe-ui"

// Fields rather than a ticket object: the three call sites hold three different ticket
// shapes, and only the event page has an event title to put in the header.
defineProps<{
	qrCode?: string | null
	attendeeName?: string | null
	attendeeEmail?: string | null
	ticketType?: string | null
	eventTitle?: string | null
	// Both ticket payloads in the app carry add-on rows: a title, and the option picked
	// where the add-on offers one.
	addOns?: { id?: string; title?: string | null; value?: string | null }[]
}>()

const open = defineModel<boolean>("open", { required: true })
</script>

<template>
	<Dialog v-model="open" :title="eventTitle || __('QR Code')" size="md">
		<div class="flex flex-col items-center gap-4">
			<div
				class="grid aspect-square w-full max-w-xs place-items-center rounded-6 border border-outline-gray-2 bg-surface-white"
			>
				<img
					v-if="qrCode"
					class="h-full w-full object-contain p-6"
					:src="qrCode"
					:alt="__('QR Code')"
				/>
				<span v-else class="text-p-base text-ink-gray-5">
					{{ __("No QR code on this ticket") }}
				</span>
			</div>

			<div class="flex flex-col items-center gap-1 text-center">
				<span v-if="ticketType" class="text-2xs-medium uppercase tracking-widest text-ink-gray-5">
					{{ ticketType }}
				</span>
				<p class="text-lg font-semibold text-ink-gray-9">{{ attendeeName }}</p>
				<p class="text-p-base text-ink-gray-6">{{ attendeeEmail }}</p>
			</div>

			<div v-if="addOns?.length" class="flex w-full flex-col items-center gap-2">
				<span class="text-2xs-medium uppercase tracking-widest text-ink-gray-5">
					{{ __("Add-Ons") }}
				</span>
				<div class="flex flex-wrap justify-center gap-2">
					<Badge
						v-for="(addOn, index) in addOns"
						:key="addOn.id || index"
						variant="subtle"
						size="lg"
					>
						{{ addOn.value ? `${addOn.title}: ${addOn.value}` : addOn.title }}
					</Badge>
				</div>
			</div>
		</div>
	</Dialog>
</template>
