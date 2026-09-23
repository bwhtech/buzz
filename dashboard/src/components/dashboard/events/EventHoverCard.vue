<script setup lang="ts">
import { bannerPattern } from "@public/js/event_banner"
import { HoverCard, dayjs } from "frappe-ui"
import { computed } from "vue"

import { timeLabel } from "@/utils/dateLabels"

const props = defineProps<{
	/** Also seeds the banner pattern, as it does everywhere else. */
	title: string
	startDate?: string | null
	startTime?: string | null
	venue?: string | null
	bannerImage?: string | null
}>()

// The class a caller passes belongs on the trigger, not on the hover card's root.
defineOptions({ inheritAttrs: false })

const banner = computed(() => ({ backgroundImage: bannerPattern(props.title) }))

// Plain dayjs: start_date is date-only, and a timezone shift moves it a day back.
// The time leads, as the one thing a reader checks first.
const startsAt = computed(() => {
	if (!props.startDate) return ""
	const date = dayjs(props.startDate).format("D MMM YYYY")
	return props.startTime ? `${timeLabel(props.startTime)}, ${date}` : date
})
</script>

<template>
	<HoverCard :hover-delay="0.15" align="start">
		<template #trigger>
			<span
				class="relative z-10 font-medium transition-colors hover:text-ink-gray-9"
				v-bind="$attrs"
				>{{ title }}</span
			>
		</template>
		<div class="w-56 space-y-2 p-2">
			<!-- The pattern also backs the image, so the slot is never blank while it loads. -->
			<img
				v-if="bannerImage"
				class="h-24 w-full rounded-4 object-cover object-top"
				:src="bannerImage"
				:style="banner"
				alt=""
			/>
			<div v-else class="h-24 w-full rounded-4" :style="banner" />

			<div class="space-y-0.5">
				<p class="font-medium text-ink-gray-8">{{ title }}</p>
				<p v-if="startsAt" class="text-sm text-ink-gray-5">{{ startsAt }}</p>
				<p v-if="venue" class="text-sm text-ink-gray-5">{{ venue }}</p>
			</div>
		</div>
	</HoverCard>
</template>
