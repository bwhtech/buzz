<script setup lang="ts">
import { computed } from "vue"

import type { ZoneStatus } from "@/types"
import { checkInTimeLabel } from "@/utils/dateLabels"

// Each zone the ticket covers is a row; tapping its circle checks the guest in there,
// or undoes it. Zones the ticket doesn't cover close the section as one quiet line.
const props = defineProps<{ zones: ZoneStatus[]; pendingZone: string | null }>()

defineEmits<{ toggle: [zone: ZoneStatus] }>()

const allowed = computed(() => props.zones.filter((zone) => zone.allowed))
const excluded = computed(() => props.zones.filter((zone) => !zone.allowed))
const checked = computed(() => allowed.value.filter((zone) => zone.checked_in_at).length)
</script>

<template>
	<section class="space-y-2">
		<div class="flex items-baseline justify-between gap-2 px-1">
			<h3 class="text-base font-semibold text-ink-gray-9">Check-in</h3>
			<span class="text-sm text-ink-gray-5 tabular-nums">
				{{ checked }} of {{ allowed.length }}
			</span>
		</div>

		<ul
			v-if="allowed.length"
			class="divide-y divide-outline-gray-1 overflow-hidden rounded-[12px] bg-surface-gray-1"
		>
			<li v-for="zone in allowed" :key="zone.name">
				<button
					type="button"
					class="zone-row flex w-full items-center gap-3 px-3.5 py-3 text-left focus-visible:focus-ring disabled:cursor-wait"
					:aria-pressed="Boolean(zone.checked_in_at)"
					:aria-label="`${zone.checked_in_at ? 'Undo check-in at' : 'Check in at'} ${zone.title}`"
					:disabled="pendingZone !== null"
					@click="$emit('toggle', zone)"
				>
					<span
						class="zone-circle flex size-[22px] shrink-0 items-center justify-center rounded-full"
						:data-on="Boolean(zone.checked_in_at) || undefined"
						:data-pending="pendingZone === zone.name || undefined"
					>
						<svg viewBox="0 0 16 16" class="size-3.5" aria-hidden="true">
							<path
								class="zone-tick"
								d="M3.5 8.5 L6.5 11.5 L12.5 4.5"
								fill="none"
								stroke="currentColor"
								stroke-width="2.2"
								stroke-linecap="round"
								stroke-linejoin="round"
							/>
						</svg>
					</span>
					<span class="min-w-0 flex-1 text-base text-pretty text-ink-gray-9">
						{{ zone.title }}
					</span>
					<span v-if="zone.checked_in_at" class="shrink-0 text-sm text-ink-gray-5 tabular-nums">
						{{ checkInTimeLabel(zone.checked_in_at) }}
					</span>
				</button>
			</li>
		</ul>

		<p v-if="excluded.length" class="px-1 text-sm text-pretty text-ink-gray-5">
			Not on this ticket: {{ excluded.map((zone) => zone.title).join(", ") }}
		</p>
	</section>
</template>

<style scoped>
.zone-row {
	transition: background-color 150ms ease;
}
@media (hover: hover) and (pointer: fine) {
	.zone-row:not(:disabled):hover {
		background-color: var(--surface-gray-2);
	}
}

.zone-circle {
	color: var(--ink-white, #fff);
	box-shadow: inset 0 0 0 1.5px var(--outline-gray-3);
	transition:
		background-color 200ms ease,
		box-shadow 200ms ease,
		opacity 150ms ease,
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.zone-row:active:not(:disabled) .zone-circle {
	transform: scale(0.9);
}
.zone-circle[data-on] {
	background-color: var(--surface-green-6, #30a66d);
	box-shadow: inset 0 0 0 1.5px transparent;
}
.zone-circle[data-pending] {
	opacity: 0.5;
}

/* The tick draws itself in on check-in and simply fades on undo. */
.zone-tick {
	stroke-dasharray: 16;
	stroke-dashoffset: 16;
	opacity: 0;
	transition: opacity 120ms ease;
}
.zone-circle[data-on] .zone-tick {
	stroke-dashoffset: 0;
	opacity: 1;
	transition:
		stroke-dashoffset 220ms cubic-bezier(0.23, 1, 0.32, 1) 60ms,
		opacity 60ms ease;
}

@media (prefers-reduced-motion: reduce) {
	.zone-circle,
	.zone-tick,
	.zone-circle[data-on] .zone-tick {
		transition: opacity 150ms ease;
	}
	.zone-row:active .zone-circle {
		transform: none;
	}
}
</style>
