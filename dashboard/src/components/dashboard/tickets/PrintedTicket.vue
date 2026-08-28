<script setup lang="ts">
import { dayjs } from "frappe-ui"
import { computed, ref } from "vue"

import QRCodeExpandDialog from "@/components/QRCodeExpandDialog.vue"
import type { TicketWithEvent } from "@/types"
import { barcodePattern } from "@/utils/ticketBarcode"

const props = defineProps<{ ticket: TicketWithEvent }>()

const showQR = ref(false)

const barcode = computed(() => ({ backgroundImage: barcodePattern(props.ticket.name) }))
// Plain dayjs: start_date is date-only, and a timezone shift moves it a day back.
const day = computed(() => dayjs(props.ticket.start_date).format("DD.MM"))
const year = computed(() => dayjs(props.ticket.start_date).format("YYYY"))

// Times arrive as a serialized timedelta ("9:00:00"), so the hour needs padding.
const doors = computed(() => {
	if (!props.ticket.start_time) return "To be announced"
	const [hour, minute] = props.ticket.start_time.split(":")
	return `${hour.padStart(2, "0")}:${minute}`
})
</script>

<template>
	<article class="flex items-stretch gap-3 text-ink-gray-9">
		<section
			class="flex-1 min-w-0 flex flex-col justify-between gap-6 rounded-8 bg-surface-gray-4 p-6 min-h-[12rem]"
		>
			<div class="flex flex-col gap-1 md:flex-row md:items-start md:justify-between md:gap-6">
				<h3
					class="font-black uppercase text-[1.375rem] md:text-[1.75rem] leading-[0.92] tracking-tight line-clamp-2"
				>
					{{ ticket.event_title }}
				</h3>
				<p
					class="font-black text-[1.375rem] md:text-[1.75rem] leading-[0.92] tracking-tight tabular-nums md:shrink-0 md:text-right"
				>
					<span>{{ day }}</span>
					<span class="ml-2 md:ml-0 md:block">{{ year }}</span>
				</p>
			</div>

			<div class="flex flex-col gap-4 md:flex-row md:gap-10 text-[10px] uppercase leading-[1.5]">
				<dl class="shrink-0 space-y-3">
					<div>
						<dt class="tracking-[0.12em] text-ink-gray-8">Doors</dt>
						<dd class="tracking-wide tabular-nums">{{ doors }}</dd>
					</div>
					<div>
						<dt class="tracking-[0.12em] text-ink-gray-8">Ticket</dt>
						<dd class="tracking-wide">{{ ticket.ticket_type }}</dd>
					</div>
				</dl>

				<dl class="min-w-0">
					<dt class="tracking-[0.12em] text-ink-gray-8">Venue</dt>
					<dd class="tracking-wide line-clamp-2">
						{{ ticket.venue || "To be announced" }}
					</dd>
				</dl>
			</div>
		</section>

		<!-- Spans only: a button may not contain flow content. -->
		<button
			type="button"
			:disabled="!ticket.qr_code"
			:aria-label="
				ticket.qr_code
					? `Show QR code for ${ticket.attendee_name}, ticket #${ticket.name}`
					: undefined
			"
			class="ticket-stub w-[27%] min-w-[10.5rem] shrink-0 flex flex-col justify-between gap-4 rounded-8 bg-surface-gray-2 p-4 text-left enabled:active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ink-gray-9"
			@click="showQR = true"
		>
			<span class="block truncate text-[9px] font-semibold uppercase tracking-[0.2em]">
				{{ ticket.event_title }}
			</span>

			<span class="flex justify-between gap-2 text-[10px] uppercase tracking-[0.12em]">
				<span class="shrink-0 text-ink-gray-8">Admits</span>
				<span class="truncate">{{ ticket.attendee_name }}</span>
			</span>

			<span class="block space-y-2">
				<span class="block h-6 w-full" :style="barcode" aria-hidden="true" />
				<span class="flex justify-between gap-2 text-[10px] uppercase tracking-[0.12em]">
					<span class="shrink-0 whitespace-nowrap text-ink-gray-8">Ticket</span>
					<span class="truncate font-mono tracking-normal">#{{ ticket.name }}</span>
				</span>
			</span>
		</button>

		<!-- Portalled, so it renders at the body and nothing here shifts. -->
		<QRCodeExpandDialog
			v-if="ticket.qr_code"
			v-model="showQR"
			:qr-code-src="ticket.qr_code"
			:alt-text="`QR code for ticket ${ticket.name}`"
		/>
	</article>
</template>

<style scoped>
/* Tear notches. The mask clips anything outside the border box, so focus rings must be inset. */
.ticket-stub {
	--notch: transparent 5px, black 6px;
	-webkit-mask-image:
		radial-gradient(circle 6px at 0 32%, var(--notch)),
		radial-gradient(circle 6px at 0 68%, var(--notch)),
		radial-gradient(circle 6px at 100% 32%, var(--notch)),
		radial-gradient(circle 6px at 100% 68%, var(--notch));
	mask-image:
		radial-gradient(circle 6px at 0 32%, var(--notch)),
		radial-gradient(circle 6px at 0 68%, var(--notch)),
		radial-gradient(circle 6px at 100% 32%, var(--notch)),
		radial-gradient(circle 6px at 100% 68%, var(--notch));
	-webkit-mask-composite: source-in;
	mask-composite: intersect;
	transition:
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1),
		background-color 160ms ease;
}

/* A touch tap fires hover and leaves it stuck. */
@media (hover: hover) and (pointer: fine) {
	.ticket-stub:not(:disabled):hover {
		background-color: var(--surface-gray-3);
	}
}

@media (prefers-reduced-motion: reduce) {
	.ticket-stub:not(:disabled):active {
		transform: none;
	}
}
</style>
