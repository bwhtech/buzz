<script setup lang="ts" generic="T extends { name: string }">
import { ErrorMessage, Icon, Skeleton, TabButtons } from "frappe-ui"

import { dayLabel, monthLabel, weekday } from "@/utils/dateLabels"
import type { MonthGroup } from "@/utils/eventGroups"
import type { TimelineTab } from "@/utils/timelineTabs"

defineProps<{
	heading: string
	icon?: string
	description?: string
	noun: string
	months: MonthGroup<T>[]
	loading?: boolean
	error?: { message: string } | null
}>()

const tab = defineModel<TimelineTab>("tab", { required: true })

const tabOptions = [
	{ label: "Upcoming", value: "upcoming" },
	{ label: "Past", value: "past" },
]
</script>

<template>
	<div class="m-auto max-w-[800px] w-full p-4 space-y-6">
		<header class="flex items-start justify-between">
			<div class="flex flex-col gap-3 items-start">
				<div class="flex gap-3 items-center">
					<div v-if="icon" class="p-2 bg-surface-gray-3 rounded-4">
						<Icon :name="icon" class="size-6" />
					</div>
					<h1 class="font-semibold text-4xl">{{ heading }}</h1>
				</div>
				<p class="text-p-base" v-if="description">{{ description }}</p>
			</div>
			<TabButtons v-model="tab" :options="tabOptions" size="md" />
		</header>

		<div v-if="$slots.controls" class="flex items-center justify-between gap-4">
			<slot name="controls" />
		</div>

		<ErrorMessage v-if="error" :message="error.message" />

		<!-- The timeline's own shape, held while the rows load: a spinner would say less
		     and move the page under the reader once the cards arrive. -->
		<div v-else-if="loading" class="space-y-6" aria-busy="true">
			<span class="sr-only">Loading {{ noun }}…</span>
			<Skeleton class="h-6 w-40 rounded-4" />
			<div v-for="row in 3" :key="row" class="grid grid-cols-[6rem_1fr] gap-4">
				<div class="space-y-2 pt-1">
					<Skeleton class="h-4 w-14 rounded-4" />
					<Skeleton class="h-4 w-20 rounded-4" />
				</div>
				<div class="pb-7 pl-6">
					<Skeleton class="h-28 w-full rounded-8" />
				</div>
			</div>
		</div>

		<div v-else class="relative space-y-6">
			<section v-for="month in months" :key="month.month" class="space-y-4">
				<h2 class="relative bg-surface-elevation-1 py-1 text-xl font-semibold text-ink-gray-8">
					{{ monthLabel(month.month) }}
				</h2>

				<div v-for="day in month.days" :key="day.date" class="grid grid-cols-[6rem_1fr] gap-4">
					<div class="pt-1">
						<p class="font-semibold text-ink-gray-8">{{ dayLabel(day.date) }}</p>
						<p class="text-base text-ink-gray-5">{{ weekday(day.date) }}</p>
					</div>

					<div class="relative space-y-1 pl-6 pb-7">
						<div class="absolute -left-4 flex flex-col items-center h-full">
							<span class="size-2 rounded-full bg-surface-gray-4" aria-hidden="true" />
							<div
								class="w-px h-full bg-gradient-to-b from-outline-gray-2 from-75% to-transparent"
							></div>
						</div>

						<div class="space-y-6">
							<template v-for="item in day.events" :key="item.name">
								<slot :item="item" />
							</template>
						</div>
					</div>
				</div>
			</section>
		</div>

		<!-- A div, not a p: the slot takes a block component. -->
		<div v-if="!months.length && !loading && !error">
			<slot name="empty-state">
				<p class="text-base text-ink-gray-5">No {{ tab }} {{ noun }}.</p>
			</slot>
		</div>
	</div>
</template>
