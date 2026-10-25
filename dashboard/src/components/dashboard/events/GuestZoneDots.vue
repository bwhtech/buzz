<script setup lang="ts">
import { HoverCard, ItemListRow, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import type { ZoneStatus } from "@/types"

const props = defineProps<{ zones: ZoneStatus[] }>()

const status = (zone: ZoneStatus) => {
	if (zone.checked_in_at) return dayjsLocal(zone.checked_in_at).format("h:mm A")
	return zone.allowed ? "Not checked in" : "Not allowed"
}

const dotClass = (zone: ZoneStatus) => {
	if (zone.checked_in_at) return "bg-surface-green-6"
	return zone.allowed ? "bg-surface-gray-4" : "border border-outline-gray-4"
}

const checkedIn = computed(() => props.zones.filter((zone) => zone.checked_in_at).length)
const allowed = computed(() => props.zones.filter((zone) => zone.allowed).length)

const summary = computed(() =>
	props.zones.map((zone) => `${zone.title}: ${status(zone)}`).join(", "),
)
</script>

<template>
	<!-- One dot per enabled zone, so a glance down the list shows who has been where. -->
	<HoverCard :hover-delay="150" side="bottom" align="end">
		<template #trigger>
			<span class="flex shrink-0 gap-1 p-1" role="img" :aria-label="summary">
				<span
					v-for="zone in zones"
					:key="zone.name"
					class="size-2 rounded-full transition-colors duration-200 ease-out"
					:class="dotClass(zone)"
				/>
			</span>
		</template>

		<div class="flex w-72 flex-col gap-0.5 p-2">
			<div class="flex justify-between gap-3 px-2 pb-1.5 text-xs text-ink-gray-5">
				<span>Zones</span>
				<span class="tabular-nums">{{ checkedIn }} of {{ allowed }} zones checked in</span>
			</div>
			<ItemListRow v-for="zone in zones" :key="zone.name" :disabled="!zone.allowed">
				<template #prefix>
					<span class="size-2 shrink-0 rounded-full" :class="dotClass(zone)" />
				</template>
				<span class="truncate" :title="zone.title">{{ zone.title }}</span>
				<template #suffix>
					<span
						class="text-sm tabular-nums"
						:class="zone.checked_in_at ? 'text-ink-gray-8' : 'text-ink-gray-5'"
					>
						{{ status(zone) }}
					</span>
				</template>
			</ItemListRow>
		</div>
	</HoverCard>
</template>
