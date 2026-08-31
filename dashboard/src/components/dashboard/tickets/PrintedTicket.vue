<script setup lang="ts">
import { dayjs } from "frappe-ui"
import { computed } from "vue"

import type { TicketWithEvent } from "@/types"
import { bannerPattern } from "@/utils/eventBanner"
import { barcodePattern } from "@/utils/ticketBarcode"

const props = defineProps<{ ticket: TicketWithEvent; bannerImage?: string | null }>()

const emit = defineEmits<{ open: [] }>()

// Bars stacked down the stub, tiled to fill whatever height it has.
const barcode = computed(() => ({
	backgroundImage: barcodePattern(props.ticket.name, "180deg"),
	backgroundSize: "100% 1rem",
	backgroundRepeat: "repeat-y",
}))
const pattern = computed(() => ({ backgroundImage: bannerPattern(props.ticket.event_title) }))
const date = computed(() => dayjs(props.ticket.start_date).format("DD.MM.YY"))
const time = computed(() => {
	if (!props.ticket.start_time) return "TBA"
	const [hour, minute] = props.ticket.start_time.split(":")
	return `${hour.padStart(2, "0")}:${minute}`
})
</script>

<template>
	<!-- Spans only: a button may not contain flow content. -->
	<button
		type="button"
		:aria-label="`Open ticket #${ticket.name} for ${ticket.attendee_name}`"
		class="ticket flex h-40 w-full items-stretch overflow-hidden rounded-8 border border-outline-gray-2 bg-surface-white text-left text-ink-gray-9 active:scale-[0.995] focus-visible:focus-ring"
		@click="emit('open')"
	>
		<span
			class="m-3 mr-0 block w-40 shrink-0 overflow-hidden rounded-6 bg-surface-gray-2"
			:style="bannerImage ? undefined : pattern"
		>
			<img v-if="bannerImage" :src="bannerImage" alt="" class="h-full w-full object-cover" />
		</span>

		<span class="flex min-w-0 flex-1 flex-col justify-between gap-4 p-4">
			<span class="block">
				<span class="block text-2xs-medium uppercase tracking-widest text-ink-gray-5">Event</span>
				<span class="block text-4xl-bold uppercase line-clamp-2">
					{{ ticket.event_title }}
				</span>
			</span>

			<span class="flex gap-8 text-sm-semibold">
				<span class="flex shrink-0 flex-col gap-2">
					<span class="block">
						<span class="block text-2xs-medium uppercase tracking-widest text-ink-gray-5"
							>When</span
						>
						<span class="block tabular-nums">{{ date }}&nbsp;&nbsp;{{ time }}</span>
					</span>
					<span class="block">
						<span class="block text-2xs-medium uppercase tracking-widest text-ink-gray-5"
							>Ticket</span
						>
						<span class="block truncate">{{ ticket.ticket_type }}</span>
					</span>
				</span>
				<span class="block min-w-0 flex-1">
					<span class="block text-2xs-medium uppercase tracking-widest text-ink-gray-5">Venue</span>
					<span class="block line-clamp-3">{{ ticket.venue || "To be announced" }}</span>
				</span>
			</span>
		</span>

		<!-- Bars run the height of the stub, with the id turned to sit beside them. -->
		<span class="stub flex w-24 shrink-0 items-center justify-center gap-2 py-3">
			<span class="block h-full w-9" :style="barcode" aria-hidden="true" />
			<span class="[writing-mode:vertical-rl] rotate-180 font-mono text-xs">
				#{{ ticket.name }}
			</span>
		</span>
	</button>
</template>

<style scoped>
/* A row that is a button has to answer the press. The scale stays near-imperceptible
   because these are seen dozens of times a session. */
.ticket {
	transition: transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
}

/* Dashed tear line with a notch bitten out of each end. */
.stub {
	border-left: 1px dashed var(--outline-gray-3);
	--notch: transparent 6px, black 7px;
	-webkit-mask-image:
		radial-gradient(circle 7px at 0 0, var(--notch)),
		radial-gradient(circle 7px at 0 100%, var(--notch));
	mask-image:
		radial-gradient(circle 7px at 0 0, var(--notch)),
		radial-gradient(circle 7px at 0 100%, var(--notch));
	-webkit-mask-composite: source-in;
	mask-composite: intersect;
}

@media (prefers-reduced-motion: reduce) {
	.ticket {
		transition: none;
	}
	.ticket:active {
		transform: none;
	}
}
</style>
