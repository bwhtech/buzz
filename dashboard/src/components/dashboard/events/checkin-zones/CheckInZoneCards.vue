<script setup lang="ts">
import { Badge, Button, Progress } from "frappe-ui"
import { computed, ref } from "vue"

import type { GuestZone } from "@/types"

import CheckInZoneDrawer from "./CheckInZoneDrawer.vue"
import {
	type CheckInZone,
	useCheckInZones,
	useEventTicketTypes,
	zoneRulesLabel,
} from "./checkInZones"

// `readOnly` hides editing, for a member who cannot edit the event.
const props = defineProps<{ event: string; stats: GuestZone[]; readOnly?: boolean }>()
const emit = defineEmits<{ changed: [] }>()

const zones = useCheckInZones(props.event)
const ticketTypes = useEventTicketTypes(props.event)

const isDrawerOpen = ref(false)
const editing = ref<CheckInZone | null>(null)

function card(stat: GuestZone, zone: CheckInZone | null) {
	const checkedIn = stat.checked_in ?? 0
	const eligible = stat.eligible ?? 0
	return {
		...stat,
		zone,
		enabled: zone ? Boolean(zone.enabled) : true,
		meta: zone ? zoneRulesLabel(zone, ticketTypes.data ?? []) : "",
		checkedIn,
		eligible,
		percent: eligible ? Math.round((checkedIn / eligible) * 100) : 0,
	}
}

// Stats cover enabled zones only; disabled ones follow, so they can be turned back on.
const cards = computed(() => {
	const enabled = props.stats.map((stat) =>
		card(stat, zones.data?.find((row) => row.name === stat.name) ?? null),
	)
	const disabled = (zones.data ?? [])
		.filter((zone) => !zone.enabled)
		.map((zone) => card({ name: zone.name, title: zone.title, is_default: false }, zone))
	return [...enabled, ...disabled]
})

function edit(zone: CheckInZone | null) {
	editing.value = zone
	isDrawerOpen.value = true
}
// Enabling or disabling a zone changes which ones have stats, as well as its own row.
function onSaved() {
	zones.reload()
	emit("changed")
}
</script>

<template>
	<div class="grid grid-cols-[repeat(auto-fill,minmax(12.5rem,1fr))] gap-2">
		<div
			v-for="card in cards"
			:key="card.name"
			class="flex flex-col gap-2.5 rounded-5 border border-outline-gray-2 py-3 pl-3.5 pr-3"
			:class="card.enabled ? 'bg-surface-base' : 'bg-surface-gray-1'"
		>
			<div class="flex min-h-5 items-center gap-1.5">
				<span class="min-w-0 truncate text-base font-medium text-ink-gray-9">
					{{ card.title }}
				</span>
				<Badge v-if="card.is_default" size="sm" :label="__('Default')" />
				<Badge v-if="!card.enabled" size="sm" theme="amber" :label="__('Disabled')" />
				<Button
					v-if="card.zone && !readOnly"
					class="-my-1.5 -mr-1 ml-auto"
					variant="ghost"
					size="sm"
					icon="lucide-pencil"
					:aria-label="__('Edit zone {0}', [card.title])"
					@click="edit(card.zone)"
				/>
			</div>

			<p class="min-h-4 truncate text-p-xs text-ink-gray-5" :title="card.meta">{{ card.meta }}</p>

			<div v-if="card.enabled" class="flex flex-col gap-1.5">
				<div class="flex justify-between gap-2 text-xs tabular-nums">
					<span class="font-medium text-ink-gray-8">
						{{ card.checkedIn }}
						<span class="font-normal text-ink-gray-5">/ {{ card.eligible }} {{ __("in") }}</span>
					</span>
					<span class="text-ink-gray-5">{{ card.percent }}%</span>
				</div>
				<Progress :value="card.percent" size="md" />
			</div>
		</div>

		<button
			v-if="!readOnly"
			type="button"
			class="flex min-h-24 items-center justify-center gap-1.5 rounded-5 border border-dashed border-outline-gray-3 text-sm text-ink-gray-5 transition-[background-color,color,transform] duration-150 ease-out hover:bg-surface-gray-1 hover:text-ink-gray-8 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 motion-reduce:transition-none"
			@click="edit(null)"
		>
			<span class="lucide-plus size-4" aria-hidden="true" />
			{{ __("Add zone") }}
		</button>
	</div>

	<CheckInZoneDrawer
		v-model:open="isDrawerOpen"
		:event="event"
		:zone="editing"
		:zones="zones"
		:ticket-types="ticketTypes.data ?? []"
		@saved="onSaved"
	/>
</template>
