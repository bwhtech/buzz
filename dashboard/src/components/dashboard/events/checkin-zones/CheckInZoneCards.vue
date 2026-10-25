<script setup lang="ts">
import { Badge, Button } from "frappe-ui"
import { computed, ref } from "vue"

import type { GuestZone } from "@/types"

import CheckInZoneDrawer from "./CheckInZoneDrawer.vue"
import { type CheckInZone, useCheckInZones, useEventTicketTypes } from "./checkInZones"

const props = defineProps<{ event: string; stats: GuestZone[] }>()
// The zone the guest list is narrowed to, empty for every guest.
const selected = defineModel<string>({ required: true })
const emit = defineEmits<{ changed: [] }>()

const zones = useCheckInZones(props.event)
const ticketTypes = useEventTicketTypes(props.event)

const isDrawerOpen = ref(false)
const editing = ref<CheckInZone | null>(null)

const ticketTypeTitles = computed(
	() => new Map((ticketTypes.data ?? []).map((row) => [row.name, row.title])),
)

const cards = computed(() =>
	props.stats.map((stat) => {
		const zone = zones.data?.find((row) => row.name === stat.name) ?? null
		const checkedIn = stat.checked_in ?? 0
		const eligible = stat.eligible ?? 0
		return {
			...stat,
			zone,
			meta: zone ? describe(zone) : "",
			checkedIn,
			eligible,
			percent: eligible ? Math.round((checkedIn / eligible) * 100) : 0,
		}
	}),
)

function describe(zone: CheckInZone) {
	const tickets = zone.ticket_types.length
		? __("{0} only", [
				zone.ticket_types
					.map((row) => ticketTypeTitles.value.get(row.ticket_type) ?? row.ticket_type)
					.join(", "),
			])
		: __("All tickets")
	return `${__(zone.repeat_rule)} · ${tickets}`
}

function edit(zone: CheckInZone | null) {
	editing.value = zone
	isDrawerOpen.value = true
}

// A zone turned off or deleted can no longer narrow the list.
function onSaved() {
	const zone = zones.data?.find((row) => row.name === selected.value)
	if (selected.value && !zone?.enabled) selected.value = ""
	emit("changed")
}

const toggle = (name: string) => (selected.value = selected.value === name ? "" : name)
</script>

<template>
	<div class="grid grid-cols-[repeat(auto-fill,minmax(12.5rem,1fr))] gap-2">
		<div
			v-for="card in cards"
			:key="card.name"
			class="relative flex flex-col gap-2.5 rounded-5 border bg-surface-base py-3 pl-3.5 pr-3 transition-[border-color,box-shadow,transform] duration-150 ease-out has-[>button:active]:scale-[0.98] motion-reduce:transition-none"
			:class="
				selected === card.name
					? 'border-outline-gray-4 shadow-sm'
					: 'border-outline-gray-2 hover:border-outline-gray-3'
			"
		>
			<div class="flex min-h-5 items-center gap-1.5">
				<!-- The whole card filters the list; the edit button sits above the stretched area. -->
				<button
					type="button"
					class="min-w-0 truncate text-left text-base font-medium text-ink-gray-9 after:absolute after:inset-0 after:rounded-5 focus-visible:outline-none focus-visible:after:ring-2 focus-visible:after:ring-outline-gray-3"
					:aria-pressed="selected === card.name"
					@click="toggle(card.name)"
				>
					{{ card.title }}
				</button>
				<Badge v-if="card.is_default" size="sm" :label="__('Default')" />
				<Button
					v-if="card.zone"
					class="relative -my-1.5 -mr-1 ml-auto"
					variant="ghost"
					size="sm"
					icon="lucide-pencil"
					:aria-label="__('Edit zone {0}', [card.title])"
					@click="edit(card.zone)"
				/>
			</div>

			<p class="min-h-4 truncate text-p-xs text-ink-gray-5" :title="card.meta">{{ card.meta }}</p>

			<div class="flex flex-col gap-1.5">
				<div class="flex justify-between gap-2 text-xs tabular-nums">
					<span class="font-medium text-ink-gray-8">
						{{ card.checkedIn }}
						<span class="font-normal text-ink-gray-5">/ {{ card.eligible }} {{ __("in") }}</span>
					</span>
					<span class="text-ink-gray-5">{{ card.percent }}%</span>
				</div>
				<div class="h-1 overflow-hidden rounded-full bg-surface-gray-2">
					<div
						class="h-full rounded-full bg-surface-green-6 transition-[width] duration-300 ease-out motion-reduce:transition-none"
						:style="{ width: `${card.percent}%` }"
					/>
				</div>
			</div>
		</div>

		<button
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
