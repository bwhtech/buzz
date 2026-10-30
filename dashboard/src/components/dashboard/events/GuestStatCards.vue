<script setup lang="ts">
import { ChartCard, NumberCard } from "frappe-ui/charts"
import { computed } from "vue"

import type { EventGuests, GuestZone, RegistrationTrend } from "@/types"

const props = defineProps<{
	trend: RegistrationTrend | null
	guests: EventGuests | null
	// The zone the list is narrowed to; null counts every zone.
	zone: GuestZone | null
	loading: boolean
}>()

// One frappe-ui card surface for all three, at the radius the zone cards below use.
const CARD = "!rounded-5 !border-outline-gray-2 !bg-surface-base"

// Gray steps rather than hues: a ticket type is a category, not a state.
const SHADES = ["bg-surface-gray-9", "bg-surface-gray-6", "bg-surface-gray-4", "bg-surface-gray-3"]

const sinceYesterday = computed(() => {
	const totals = new Map<string, number>()
	for (const row of props.trend?.per_day ?? [])
		totals.set(row.date, (totals.get(row.date) || 0) + row.count)
	const days = [...totals.values()]
	return days.length < 2 ? null : days[days.length - 1] - days[days.length - 2]
})

const checkedIn = computed(() =>
	props.zone ? (props.zone.checked_in ?? 0) : (props.guests?.checked_in_any_zone ?? 0),
)
const checkedInOf = computed(() =>
	props.zone ? (props.zone.eligible ?? 0) : (props.guests?.total ?? 0),
)

const ticketTypes = computed(() => {
	const total = props.trend?.total || 0
	return (props.trend?.by_ticket_type ?? [])
		.filter((row) => row.count)
		.map((row, index) => ({
			title: row.ticket_type || __("Unnamed"),
			count: row.count,
			percent: total ? (row.count / total) * 100 : 0,
			shade: SHADES[index % SHADES.length],
		}))
})
</script>

<template>
	<div class="grid gap-2 sm:grid-cols-3">
		<NumberCard
			:class="CARD"
			:title="__('Registered')"
			:value="trend?.total ?? null"
			:loading="!trend"
			:delta="sinceYesterday"
			:delta-caption="__('vs yesterday')"
		/>

		<NumberCard
			:class="CARD"
			:title="zone ? __('Checked in at {0}', [zone.title]) : __('Checked in')"
			:value="guests ? checkedIn : null"
			:target="checkedInOf"
			:loading="loading && !guests"
		/>

		<ChartCard :class="CARD">
			<div class="flex flex-col gap-2.5">
				<span class="text-sm text-ink-gray-5">{{ __("Ticket types") }}</span>
				<div class="flex h-1.5 gap-0.5 overflow-hidden rounded-full bg-surface-gray-2">
					<div
						v-for="ticketType in ticketTypes"
						:key="ticketType.title"
						:class="ticketType.shade"
						:style="{ width: `${ticketType.percent}%` }"
					/>
				</div>
				<div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-ink-gray-6">
					<span
						v-for="ticketType in ticketTypes"
						:key="ticketType.title"
						class="inline-flex min-w-0 items-center gap-1.5"
					>
						<span class="size-1.5 shrink-0 rounded-full" :class="ticketType.shade" />
						<span class="truncate">{{ ticketType.title }}</span>
						<span class="tabular-nums text-ink-gray-9">{{ ticketType.count }}</span>
					</span>
					<span v-if="trend && !ticketTypes.length" class="text-ink-gray-5">
						{{ __("No tickets yet") }}
					</span>
				</div>
			</div>
		</ChartCard>
	</div>
</template>
