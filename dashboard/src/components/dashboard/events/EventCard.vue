<script setup lang="ts">
import { Avatar, Badge, Button } from "frappe-ui"
import { computed } from "vue"

import type { MyEvent } from "@/types"
import { dayLabel, timeLabel } from "@/utils/dateLabels"
import { bannerPattern } from "@/utils/eventBanner"

// The Events page files cards under a date heading; a standalone list has to
// carry the date on the card itself.
const props = withDefaults(
	defineProps<{
		event: MyEvent
		showDate?: boolean
		showManage?: boolean
	}>(),
	{ showManage: true },
)

// Manage is the only way into the desk view; the card itself opens the drawer.
const canManage = computed(() => props.showManage && props.event.is_host)

const startTime = computed(() => (props.event.start_time ? timeLabel(props.event.start_time) : ""))

const banner = computed(() => ({ backgroundImage: bannerPattern(props.event.name) }))

// Only a host can fix a missing venue; for everyone else it is news, not a warning.
const venue = computed(() => {
	if (props.event.venue) return { label: props.event.venue, icon: "lucide-map-pin", tone: "" }
	if (props.event.is_host)
		return {
			label: "Location missing",
			icon: "lucide-triangle-alert",
			tone: "text-ink-amber-6",
		}
	return { label: "Venue to be announced", icon: "lucide-map-pin-off", tone: "" }
})
</script>

<template>
	<article
		class="flex gap-4 border border-outline-gray-2 hover:border-outline-gray-3 rounded-8 p-3"
	>
		<!-- The pattern also backs the image, so the slot is never blank while it loads. -->
		<img
			v-if="event.banner_image"
			class="h-30 w-30 rounded-4 object-cover object-top"
			:src="event.banner_image"
			:style="banner"
			loading="lazy"
			alt=""
		/>
		<div v-else class="h-30 w-30 rounded-4" :style="banner" />

		<div class="flex-1 py-1 flex flex-col justify-between">
			<div class="flex-1 space-y-2">
				<p
					v-if="showDate || startTime"
					class="flex items-center gap-2 text-base tabular-nums text-ink-gray-5"
				>
					<span v-if="showDate">{{ dayLabel(event.start_date) }}</span>
					<span v-if="showDate && startTime" class="text-ink-gray-4">·</span>
					<span v-if="startTime">{{ startTime }}</span>
				</p>

				<h3 class="font-semibold text-lg text-ink-gray-8">{{ event.title }}</h3>
				<p v-if="event.team_name" class="flex items-center gap-2 text-sm text-ink-gray-6">
					<Avatar :image="event.team_logo || undefined" :label="event.team_name" size="xs" />
					By {{ event.team_name }}
				</p>
				<p class="flex items-center gap-2 text-base text-ink-gray-5">
					<span class="size-4 shrink-0" :class="[venue.icon, venue.tone]" aria-hidden="true" />
					{{ venue.label }}
				</p>
			</div>

			<div v-if="event.is_attendee || canManage" class="mt-3 flex items-end">
				<Badge v-if="event.is_attendee" theme="violet" variant="subtle" label="Attending" />
				<Button
					v-if="canManage"
					class="relative z-10 ml-auto"
					label="Manage"
					icon-right="lucide-arrow-right"
					size="sm"
					:route="`/manage/events/${event.name}`"
				/>
			</div>
		</div>
	</article>
</template>
