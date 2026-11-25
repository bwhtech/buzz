<script setup lang="ts">
import { bannerPattern } from "@public/js/event_banner"
import { Badge, Button } from "frappe-ui"
import { computed } from "vue"

import DateBadge from "@/components/common/DateBadge.vue"

import CopyLink from "./CopyLink.vue"
import type { EventSummary } from "./overviewData"

// The event as its share card: cover, status, when, where, and its link.
const props = defineProps<{ summary: EventSummary; eventId: string }>()

const detailsRoute = computed(() => ({ name: "event-details", params: { eventId: props.eventId } }))

// The same rings the event cards draw, so a coverless event still looks like itself.
const cover = computed(() => ({
	backgroundImage: props.summary.banner
		? `url("${props.summary.banner}")`
		: bannerPattern(props.summary.title),
}))
const status = computed(() =>
	props.summary.isPublished
		? { label: "Live", theme: "green" as const }
		: { label: "Draft", theme: "gray" as const },
)
</script>

<template>
	<section
		class="flex gap-5 rounded-5 border border-outline-gray-2 bg-surface-elevation-1 p-3 max-sm:flex-col"
	>
		<div
			class="aspect-[1.91/1] w-full shrink-0 rounded-4 bg-cover bg-center sm:w-[280px]"
			:style="cover"
		/>
		<div class="flex min-w-0 flex-1 flex-col gap-3 py-1 pr-1">
			<div class="flex items-center gap-2">
				<Badge :label="status.label" :theme="status.theme" variant="subtle" />
			</div>
			<h2 class="text-2xl font-semibold leading-tight tracking-[-0.01em] text-ink-gray-9">
				{{ summary.title }}
			</h2>
			<div class="flex items-center gap-3">
				<DateBadge :date="summary.startDate" size="sm" />
				<div class="min-w-0 leading-tight">
					<p class="truncate text-base font-medium text-ink-gray-8">{{ summary.dateLabel }}</p>
					<p class="truncate text-p-sm text-ink-gray-5">{{ summary.timeLabel }}</p>
				</div>
			</div>
			<div class="flex items-center gap-3">
				<span
					class="grid size-10 shrink-0 place-items-center rounded-4 border border-outline-gray-2"
					:class="summary.venueMissing ? 'text-ink-amber-6' : 'text-ink-gray-6'"
				>
					<span
						:class="summary.venueMissing ? 'lucide-triangle-alert' : 'lucide-map-pin'"
						class="size-4"
					/>
				</span>
				<div class="min-w-0 leading-tight">
					<p
						class="truncate text-base font-medium"
						:class="summary.venueMissing ? 'text-ink-amber-6' : 'text-ink-gray-8'"
					>
						{{ summary.venue }}
					</p>
					<p class="truncate text-p-sm text-ink-gray-5">{{ summary.venueDetail }}</p>
				</div>
			</div>
			<div class="mt-auto flex items-center gap-2 pt-1">
				<CopyLink v-if="summary.route" :route="summary.route" class="flex-1" />
				<Button variant="subtle" label="Edit Details" :route="detailsRoute" class="ml-auto" />
			</div>
		</div>
	</section>
</template>
