<script setup lang="ts">
import { dayjs } from "frappe-ui"
import { computed } from "vue"

import type { TicketWithEvent } from "@/types"
import { barcodePattern } from "@/utils/ticketBarcode"

// `static` renders the same paper without a press target, for a place that already
// shows the ticket's own context.
const props = defineProps<{ ticket: TicketWithEvent; static?: boolean }>()

const emit = defineEmits<{ open: [] }>()

// Bars stacked down the stub, tiled to fill whatever height it has.
const barcode = computed(() => ({
	backgroundImage: barcodePattern(props.ticket.name, "180deg"),
	backgroundSize: "100% 1rem",
	backgroundRepeat: "repeat-y",
}))
const date = computed(() => dayjs(props.ticket.start_date).format("DD.MM.YY"))
const time = computed(() => {
	if (!props.ticket.start_time) return "TBA"
	const [hour, minute] = props.ticket.start_time.split(":")
	return `${hour.padStart(2, "0")}:${minute}`
})
</script>

<template>
	<!-- The shell only draws the outline and shadow. A mask cuts a border into open arcs,
	     so the die-cut edge is traced with drop-shadow, which follows the mask instead. -->
	<div class="ticket-shell">
		<!-- Spans only: a button may not contain flow content. -->
		<component
			:is="static ? 'div' : 'button'"
			:type="static ? undefined : 'button'"
			:aria-label="static ? undefined : `Open ticket #${ticket.name} for ${ticket.attendee_name}`"
			class="ticket flex h-40 w-full items-stretch overflow-hidden bg-surface-base text-left text-ink-gray-9 focus-visible:outline-none"
			:class="{ 'is-pressable active:scale-[0.995]': !static }"
			:onClick="static ? undefined : () => emit('open')"
		>
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
						<span class="block text-2xs-medium uppercase tracking-widest text-ink-gray-5"
							>Venue</span
						>
						<span class="block line-clamp-3">{{ ticket.venue || "To be announced" }}</span>
					</span>
				</span>
			</span>

			<!-- Bars run the height of the stub, with the id turned to sit beside them. -->
			<span class="stub flex shrink-0 items-center justify-center gap-2 py-3">
				<span class="block h-full w-9" :style="barcode" aria-hidden="true" />
				<span class="[writing-mode:vertical-rl] rotate-180 font-mono text-xs">
					#{{ ticket.name }}
				</span>
			</span>
		</component>
	</div>
</template>

<style scoped>
/* The outline is a drop-shadow because it has to follow the mask's silhouette; a border
   would be cut into open arcs by the same mask that bites the notches. Drawn twice:
   one 1px drop-shadow is too washed out to read as a line, and there is no spread to
   thicken it with. */
.ticket-shell {
	--edge: var(--outline-gray-3);
	--hairline: drop-shadow(0 0 1px var(--edge)) drop-shadow(0 0 1px var(--edge));
	filter: var(--hairline);
	transition: filter 160ms ease;
}

/* The focus ring traces the same silhouette, since an outline is masked away too. */
.ticket-shell:has(.ticket:focus-visible) {
	--edge: var(--outline-gray-4);
	filter: var(--hairline) var(--hairline);
}

/* A row that is a button has to answer the press. The scale stays near-imperceptible
   because these are seen dozens of times a session. */
.ticket {
	/* Bites out of the paper: a quarter circle at each corner, and a half circle at each
	   end of the tear line. The stub width has to be stated here too, so the tear-line
	   notches land on it. */
	--stub: 6rem;
	--corner: 10px;
	--tear: 8px;
	--bite: transparent calc(var(--corner) - 1px), black var(--corner);
	--tear-bite: transparent calc(var(--tear) - 1px), black var(--tear);
	--notches:
		radial-gradient(circle var(--corner) at 0 0, var(--bite)),
		radial-gradient(circle var(--corner) at 100% 0, var(--bite)),
		radial-gradient(circle var(--corner) at 0 100%, var(--bite)),
		radial-gradient(circle var(--corner) at 100% 100%, var(--bite)),
		radial-gradient(circle var(--tear) at calc(100% - var(--stub)) 0, var(--tear-bite)),
		radial-gradient(circle var(--tear) at calc(100% - var(--stub)) 100%, var(--tear-bite));
	-webkit-mask-image: var(--notches);
	mask-image: var(--notches);
	-webkit-mask-composite: source-in;
	mask-composite: intersect;
	transition:
		transform 120ms cubic-bezier(0.23, 1, 0.32, 1),
		background-color 160ms ease;
}

/* The tear itself. Its width is what --stub above measures. */
.stub {
	width: var(--stub);
	border-left: 1px dashed var(--outline-gray-3);
}

/* A touch tap fires hover and leaves it stuck. */
@media (hover: hover) and (pointer: fine) {
	.ticket.is-pressable:hover {
		background-color: var(--surface-gray-1);
	}
}

@media (prefers-reduced-motion: reduce) {
	.ticket-shell,
	.ticket {
		transition: none;
	}
	.ticket:active {
		transform: none;
	}
}
</style>
