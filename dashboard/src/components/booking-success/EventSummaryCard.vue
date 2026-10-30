<script setup lang="ts">
import LucideArrowUpRight from "~icons/lucide/arrow-up-right"
import LucideMapPin from "~icons/lucide/map-pin"

import DateBadge from "@/components/common/DateBadge.vue"
import { useEventDateLabels } from "@/components/registration/useEventDateLabels"
import { eventUrl } from "@/utils/eventUrl"

const props = defineProps<{
	event: Record<string, any>
	venue: { venue_name: string; address?: string | null } | null
	bookingId: string
}>()

const { dateLabel, timeLabel } = useEventDateLabels(() => props.event)
</script>

<template>
	<div class="overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-base text-left">
		<div class="flex items-center gap-3.5 p-4">
			<DateBadge :date="event.start_date" />
			<div class="flex min-w-0 flex-col gap-1">
				<span class="text-base-semibold text-ink-gray-9">{{ event.title }}</span>
				<span class="text-p-sm text-ink-gray-6">
					{{ [dateLabel, timeLabel].filter(Boolean).join(" · ") }}
				</span>
			</div>
		</div>

		<div v-if="venue" class="flex items-start gap-3 border-t border-outline-gray-1 px-4 py-3.5">
			<LucideMapPin class="mt-0.5 size-4 shrink-0 text-ink-gray-5" />
			<div class="flex min-w-0 flex-col gap-0.5">
				<span class="text-base-medium text-ink-gray-8">{{ venue.venue_name }}</span>
				<span v-if="venue.address" class="text-p-sm text-ink-gray-5 text-pretty">
					{{ venue.address }}
				</span>
			</div>
		</div>

		<div
			class="flex items-center justify-between gap-3 border-t border-outline-gray-1 bg-surface-gray-1 px-4 py-2.5 text-p-sm"
		>
			<span class="text-ink-gray-5">
				{{ __("Booking") }}
				<span class="tabular-nums text-ink-gray-8">{{ bookingId }}</span>
			</span>
			<a
				v-if="event.route"
				:href="eventUrl(event.route)"
				class="flex items-center gap-1 text-ink-gray-8 hover:underline"
			>
				{{ __("View event page") }}
				<LucideArrowUpRight class="size-3.5" />
			</a>
		</div>
	</div>
</template>
