<script setup lang="ts">
import { Combobox } from "frappe-ui"
import type { ComboboxCustomOption, ComboboxSelectableOption } from "frappe-ui"
import { computed, ref } from "vue"

import {
	allTimeZones,
	zoneCity,
	zoneCountry,
	zoneGenericName,
	zoneOffsetLabel,
	zoneSearchText,
} from "@/utils/timeZones"

// The zone by its everyday name, with the offset and city underneath, sized to sit
// beside the date trigger.
defineProps<{ disabled?: boolean }>()
const timeZone = defineModel<string>({ default: "" })

// Built on first open: the full zone sweep is too slow to run while the page renders.
const hasOpened = ref(false)
const options = computed(() =>
	hasOpened.value
		? allTimeZones().map((zone) => ({ label: zoneSearchText(zone), value: zone }))
		: [],
)
const zoneOf = (item: ComboboxSelectableOption | ComboboxCustomOption) => String(item.value ?? "")

const name = computed(() => (timeZone.value ? zoneGenericName(timeZone.value) : __("Time zone")))
const detail = computed(() =>
	timeZone.value ? `${zoneOffsetLabel(timeZone.value)} · ${zoneCity(timeZone.value)}` : "",
)
</script>

<template>
	<Combobox
		v-model="timeZone"
		class="w-full"
		:options="options"
		:disabled="disabled"
		:placeholder="__('Search by city, country or zone')"
		@update:open="(open: unknown) => (hasOpened = hasOpened || Boolean(open))"
	>
		<template #trigger>
			<button
				type="button"
				class="zone flex min-h-14 w-full items-center gap-2.5 rounded-5 border border-outline-gray-2 bg-surface-base px-3.5 py-2 text-left disabled:cursor-not-allowed disabled:opacity-60"
				:disabled="disabled"
				:aria-label="__('Time zone: {0}', [name])"
			>
				<span class="lucide-globe size-[18px] shrink-0 text-ink-gray-6" aria-hidden="true" />
				<span class="flex min-w-0 flex-1 flex-col">
					<span class="truncate text-sm font-medium text-ink-gray-9">{{ name }}</span>
					<span v-if="detail" class="truncate text-xs text-ink-gray-5">{{ detail }}</span>
				</span>
			</button>
		</template>
		<template #item="{ item }">
			<div class="flex w-full items-center gap-2 overflow-hidden p-2">
				<span class="truncate text-ink-gray-8">{{ zoneCity(zoneOf(item)) }}</span>
				<span class="truncate text-ink-gray-5">{{ zoneCountry(zoneOf(item)) }}</span>
				<span class="ml-auto shrink-0 text-sm text-ink-gray-5">{{
					zoneOffsetLabel(zoneOf(item))
				}}</span>
			</div>
		</template>
	</Combobox>
</template>

<style scoped>
.zone {
	transition:
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1),
		background-color 150ms ease;
}
.zone:not(:disabled):active {
	transform: scale(0.98);
}
@media (hover: hover) and (pointer: fine) {
	.zone:not(:disabled):hover {
		background: var(--surface-gray-1);
	}
}
@media (prefers-reduced-motion: reduce) {
	.zone:active {
		transform: none;
	}
}
</style>
