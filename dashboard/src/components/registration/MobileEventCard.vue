<template>
	<div class="flex items-center gap-3">
		<img
			v-if="eventDetails.banner_image"
			:src="eventDetails.banner_image"
			:alt="eventDetails.title"
			class="size-[52px] flex-none rounded-7 border border-outline-gray-1 object-cover"
		/>
		<div class="flex min-w-0 flex-col gap-0.5">
			<span class="font-display text-[26px] uppercase leading-none text-ink-gray-9">
				{{ __(eventDetails.title) }}
			</span>
			<span class="text-p-sm text-ink-gray-5">
				{{ [dateLabel, eventDetails.venue_name].filter(Boolean).join(" · ") }}
			</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useEventDateLabels } from "./useEventDateLabels"

const props = defineProps<{ eventDetails: Record<string, any> }>()
const { dateLabel } = useEventDateLabels(() => props.eventDetails)
</script>
