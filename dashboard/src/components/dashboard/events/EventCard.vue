<script setup lang="ts">
import { bannerPattern } from "@public/js/event_banner"
import { Avatar, Badge, Button } from "frappe-ui"
import { computed, ref } from "vue"

import type { MyEvent, TeamEvent } from "@/types"
import { dayLabel, timeLabel } from "@/utils/dateLabels"

// The Events page files cards under a date heading; a standalone list has to
// carry the date on the card itself.
// A team calendar row may be an external event, which has no Buzz page or drawer of its own.
const props = defineProps<{
	event: MyEvent & Partial<Pick<TeamEvent, "is_external" | "event_url">>
	showDate?: boolean
}>()

const emit = defineEmits<{ open: [] }>()

// Manage is the only way into the desk view; the card itself opens the drawer.
const canManage = computed(() => props.event.is_host)

// An external event opens where it lives, on its own platform.
const externalUrl = computed(() => (props.event.is_external && props.event.event_url) || "")

const startTime = computed(() => (props.event.start_time ? timeLabel(props.event.start_time) : ""))

// A multi-day event always carries its range: the timeline files it under one day only.
const dateLabel = computed(() => {
	const { start_date, end_date } = props.event
	if (end_date && end_date !== start_date) return `${dayLabel(start_date)} – ${dayLabel(end_date)}`
	return props.showDate ? dayLabel(start_date) : ""
})

const bannerFailed = ref(false)

const banner = computed(() => ({ backgroundImage: bannerPattern(props.event.title) }))

// Only a host can fix a missing venue; for everyone else it is news, not a warning.
const venue = computed(() => {
	if (props.event.medium === "Online") return { label: "Online", icon: "lucide-video", tone: "" }
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
		class="event-card relative flex gap-4 border border-outline-gray-2 hover:border-outline-gray-3 rounded-8 p-3"
	>
		<!-- Overlay rather than a wrapper: Manage cannot legally nest inside a button.
		     It sits above the overlay, so both targets work and both are focusable. -->
		<!-- Static tags: a dynamic `is="button"` resolves to frappe-ui's global Button. -->
		<a
			v-if="externalUrl"
			:href="externalUrl"
			target="_blank"
			rel="noopener"
			:aria-label="`Open ${event.title} in a new tab`"
			class="event-card-overlay absolute inset-0 rounded-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-3"
		/>
		<button
			v-else
			type="button"
			:aria-label="`Open ${event.title}`"
			class="event-card-overlay absolute inset-0 rounded-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-3"
			@click="emit('open')"
		/>

		<!-- The pattern also backs the image, so the slot is never blank while it loads. -->
		<img
			v-if="event.banner_image && !bannerFailed"
			class="size-20 shrink-0 rounded-4 object-cover object-top md:size-30"
			:src="event.banner_image"
			:style="banner"
			loading="lazy"
			alt=""
			@error="bannerFailed = true"
		/>
		<div v-else class="size-20 shrink-0 rounded-4 md:size-30" :style="banner" />

		<div class="min-w-0 flex-1 py-1 flex flex-col justify-between">
			<div class="flex-1 space-y-2">
				<p
					v-if="dateLabel || startTime"
					class="flex flex-wrap items-center gap-x-2 text-base tabular-nums text-ink-gray-5"
				>
					<span v-if="dateLabel" class="whitespace-nowrap">{{ dateLabel }}</span>
					<span v-if="dateLabel && startTime" class="text-ink-gray-4">·</span>
					<span v-if="startTime">{{ startTime }}</span>
				</p>

				<h3
					class="font-semibold text-lg text-ink-gray-8 hyphens-auto [overflow-wrap:anywhere] max-md:line-clamp-3"
					:title="event.title"
				>
					{{ event.title }}
				</h3>
				<!-- Top-aligned with the first line: team names and venues are long enough to wrap. -->
				<p v-if="event.team_name" class="flex items-start gap-2 text-sm text-ink-gray-6">
					<Avatar
						class="mt-px"
						:image="event.team_logo || undefined"
						:label="event.team_name"
						size="xs"
					/>
					<span class="min-w-0 [overflow-wrap:anywhere]">By {{ event.team_name }}</span>
				</p>
				<p class="flex items-start gap-2 text-base text-ink-gray-5">
					<span
						class="mt-0.5 size-4 shrink-0"
						:class="[venue.icon, venue.tone]"
						aria-hidden="true"
					/>
					<span class="min-w-0 [overflow-wrap:anywhere] max-md:line-clamp-2" :title="venue.label">
						{{ venue.label }}
					</span>
				</p>
			</div>

			<div
				v-if="event.is_attendee || event.is_external || canManage"
				class="mt-3 flex items-end gap-2"
			>
				<Badge v-if="event.is_attendee" theme="violet" variant="subtle" label="Attending" />
				<Badge v-if="event.is_external" variant="subtle" :label="__('External')" />
				<Button
					v-if="canManage"
					class="relative z-10 ml-auto max-md:hidden"
					label="Manage"
					icon-right="lucide-arrow-right"
					size="sm"
					:route="`/manage/events/${event.name}`"
				/>
			</div>
		</div>

		<span
			class="lucide-chevron-right size-4 shrink-0 self-center text-ink-gray-4 md:hidden"
			aria-hidden="true"
		/>
	</article>
</template>

<style scoped>
/* A card that is a button has to answer the press. The scale stays near-imperceptible
   because these are seen dozens of times a session. */
.event-card {
	transition: transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
}
/* Only the overlay opens the drawer, so Manage does not press the card with it. */
.event-card:has(> .event-card-overlay:active) {
	transform: scale(0.995);
}

@media (prefers-reduced-motion: reduce) {
	.event-card {
		transition: none;
	}
	.event-card:has(> .event-card-overlay:active) {
		transform: none;
	}
}
</style>
