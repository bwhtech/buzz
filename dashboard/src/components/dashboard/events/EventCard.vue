<script setup lang="ts">
import "@public/themes/event_card.css"
import { bannerPattern } from "@public/js/event_banner"
import { Avatar, Badge, Button, dayjs } from "frappe-ui"
import { computed, ref } from "vue"

import DateBadge from "@/components/common/DateBadge.vue"
import type { EventCardLayout } from "@/composables/useEventCardLayout"
import type { MyEvent, TeamEvent } from "@/types"
import { dayLabel, rangeLabel, timeLabel } from "@/utils/dateLabels"

// The timeline files row cards under a date heading; a standalone list has to carry the date
// on the card itself. A cover card always does, on its cover.
// A team calendar row may be an external event, which has no Buzz page or drawer of its own.
const props = withDefaults(
	defineProps<{
		event: MyEvent & Partial<Pick<TeamEvent, "is_external" | "event_url">>
		layout?: EventCardLayout
		showDate?: boolean
	}>(),
	{ layout: "row" },
)

const emit = defineEmits<{ open: [] }>()

defineSlots<{
	/** Beside the time on a row, on the cover's corner on a cover card. */
	status?: () => unknown
	/** Trailing CTA; defaults to Manage for hosts. */
	actions?: () => unknown
}>()

// An external event opens where it lives, on its own platform.
const externalUrl = computed(() => (props.event.is_external && props.event.event_url) || "")

const start = computed(() => dayjs(props.event.start_date))
const startTime = computed(() => (props.event.start_time ? timeLabel(props.event.start_time) : ""))

// A multi-day event always carries its range: the timeline files it under one day only.
const dateLabel = computed(() => {
	const { start_date, end_date } = props.event
	if (end_date && end_date !== start_date) return rangeLabel(start_date, end_date)
	return props.showDate ? dayLabel(start_date) : ""
})

// Solid on a cover, so the badges read over any image.
const badgeVariant = computed(() => (props.layout === "cover" ? "solid" : "subtle"))

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
			tone: "buzz-event-card-warning",
		}
	return { label: "Venue to be announced", icon: "lucide-map-pin-off", tone: "" }
})
</script>

<template>
	<article class="buzz-event-card" :data-layout="layout">
		<!-- Static tags: a dynamic `is="button"` resolves to frappe-ui's global Button. -->
		<a
			v-if="externalUrl"
			class="buzz-event-card-target"
			:href="externalUrl"
			target="_blank"
			rel="noopener"
			:aria-label="`Open ${event.title} in a new tab`"
		/>
		<button
			v-else
			type="button"
			class="buzz-event-card-target"
			:aria-label="`Open ${event.title}`"
			@click="emit('open')"
		/>

		<div class="buzz-event-card-cover">
			<!-- The pattern also backs the image, so the slot is never blank while it loads. -->
			<img
				v-if="event.banner_image && !bannerFailed"
				class="buzz-event-card-image"
				:src="event.banner_image"
				:style="banner"
				loading="lazy"
				decoding="async"
				alt=""
				@error="bannerFailed = true"
			/>
			<div v-else class="buzz-event-card-image" :style="banner" />
			<DateBadge :date="event.start_date" size="sm" />
		</div>

		<div class="buzz-event-card-body">
			<p v-if="dateLabel || startTime || layout === 'cover'" class="buzz-event-card-time">
				<span v-if="dateLabel" class="whitespace-nowrap">{{ dateLabel }}</span>
				<span v-else class="buzz-event-card-weekday">
					<span>{{ start.format("ddd") }}</span>
					<span v-if="startTime" class="buzz-event-card-separator">·</span>
				</span>
				<span v-if="dateLabel && startTime" class="buzz-event-card-separator">·</span>
				<span v-if="startTime">{{ startTime }}</span>
			</p>

			<h3 class="buzz-event-card-title" :title="event.title" dir="auto">{{ event.title }}</h3>

			<p class="buzz-event-card-meta">
				<span v-if="event.team_name" class="buzz-event-card-meta-item">
					<Avatar :image="event.team_logo || undefined" :label="event.team_name" size="xs" />
					<span class="buzz-event-card-truncate" :title="event.team_name" dir="auto">{{
						event.team_name
					}}</span>
				</span>
				<span class="buzz-event-card-meta-item" :class="venue.tone">
					<span class="size-3.5" :class="venue.icon" aria-hidden="true" />
					<span class="line-clamp-2" :title="venue.label" dir="auto">{{ venue.label }}</span>
				</span>
			</p>
		</div>

		<div
			v-if="$slots.status || event.is_attendee || event.is_external"
			class="buzz-event-card-status"
		>
			<slot name="status">
				<Badge v-if="event.is_attendee" theme="violet" :variant="badgeVariant" label="Attending" />
				<Badge v-if="event.is_external" :variant="badgeVariant" :label="__('External')" />
			</slot>
		</div>

		<div v-if="$slots.actions || event.is_host" class="buzz-event-card-actions">
			<!-- Manage is the only way into the desk view; the card itself opens the drawer. -->
			<slot name="actions">
				<Button
					label="Manage"
					icon-right="lucide-arrow-right"
					size="sm"
					:route="`/manage/events/${event.name}`"
				/>
			</slot>
		</div>
	</article>
</template>
