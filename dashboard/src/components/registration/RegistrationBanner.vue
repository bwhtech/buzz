<template>
	<header class="border-y border-outline-gray-1 bg-surface-gray-1">
		<div class="mx-auto flex max-w-6xl flex-wrap items-center gap-6 p-6">
			<img
				v-if="eventDetails.banner_image"
				:src="eventDetails.banner_image"
				:alt="eventDetails.title"
				class="h-28 w-[200px] flex-none rounded-5 border border-outline-gray-2 object-cover"
			/>
			<div class="flex min-w-0 flex-[1_1_320px] flex-col gap-3">
				<h1 class="font-display text-[44px] uppercase leading-none text-ink-gray-9 text-balance">
					{{ __(eventDetails.title) }}
				</h1>
				<div class="flex flex-wrap gap-5">
					<div v-if="eventDetails.start_date" class="flex items-center gap-2.5">
						<div
							class="w-10 flex-none overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-base text-center"
						>
							<div
								class="border-b border-outline-gray-1 py-0.5 text-[10px] font-semibold uppercase tracking-[0.06em] text-ink-gray-5"
							>
								{{ startDate.format("MMM") }}
							</div>
							<div class="py-0.5 font-display text-xl leading-tight text-ink-gray-9">
								{{ startDate.format("D") }}
							</div>
						</div>
						<div class="flex flex-col gap-0.5">
							<span class="text-base font-semibold text-ink-gray-9">{{ dateLabel }}</span>
							<span v-if="timeLabel" class="text-p-sm text-ink-gray-5">{{ timeLabel }}</span>
						</div>
					</div>
					<div v-if="venueLabel" class="flex items-center gap-2.5">
						<div
							class="flex size-10 flex-none items-center justify-center rounded-5 border border-outline-gray-2 bg-surface-base text-ink-gray-6"
						>
							<LucideMapPin class="size-4" />
						</div>
						<span class="text-base font-semibold text-ink-gray-9">{{ venueLabel }}</span>
					</div>
				</div>
			</div>
			<HoldPill v-if="secondsLeft" :seconds-left="secondsLeft" />
		</div>
	</header>
</template>

<script setup lang="ts">
import { computed } from "vue"
import LucideMapPin from "~icons/lucide/map-pin"

import HoldPill from "./HoldPill.vue"
import { useEventDateLabels } from "./useEventDateLabels"

const props = defineProps<{
	eventDetails: Record<string, any>
	secondsLeft: number | null
}>()

const { startDate, dateLabel, timeLabel } = useEventDateLabels(() => props.eventDetails)

const venueLabel = computed(
	() =>
		props.eventDetails.venue_name || (props.eventDetails.medium === "Online" ? __("Online") : ""),
)
</script>
