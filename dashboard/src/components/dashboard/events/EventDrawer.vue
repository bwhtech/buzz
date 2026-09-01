<script setup lang="ts">
import { Alert, Avatar, Button, Icon, toast } from "frappe-ui"
import { dayjs } from "frappe-ui"
import { computed } from "vue"

import {
	Drawer,
	DrawerClose,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import EventCountdownPill from "@/components/dashboard/events/EventCountdownPill.vue"
import EventMyTickets from "@/components/dashboard/events/EventMyTickets.vue"
import type { MyEvent } from "@/types"
import { timeLabel12Hour } from "@/utils/dateLabels"
import { bannerPattern } from "@/utils/eventBanner"
import { copyEventUrl, eventUrl } from "@/utils/eventUrl"

const props = defineProps<{ event: MyEvent | null }>()

const open = defineModel<boolean>("open", { required: true })

// The banner also backs a missing image, so the slot is never blank while it loads.
const banner = computed(() => ({
	backgroundImage: props.event ? bannerPattern(props.event.name) : "",
}))

// The calendar chip wants the parts, not a formatted string.
const day = computed(() => ({
	month: props.event ? dayjs(props.event.start_date).format("MMM").toUpperCase() : "",
	date: props.event ? dayjs(props.event.start_date).format("D") : "",
}))

// A run that ends on a later day cannot state its times as one range — "09:00 – 17:00"
// would read as a single afternoon — so each end gets its own line with its own date.
const laterEndDate = computed(() => {
	const event = props.event
	if (!event?.end_date || event.end_date === event.start_date) return null
	return event.end_date
})

const startsAt = computed(() => {
	if (!props.event) return ""
	const date = dayjs(props.event.start_date)
	if (!laterEndDate.value) return date.format("dddd, D MMMM")
	const time = props.event.start_time ? `, ${timeLabel12Hour(props.event.start_time)}` : ""
	return `${date.format("ddd, D MMM")}${time}`
})

async function copyLink() {
	if (!props.event?.route) return
	try {
		await copyEventUrl(props.event.route)
		toast.success("Event link copied")
	} catch {
		// Clipboard access is refused outside a secure context, and on an http:// host
		// in development that is every time.
		toast.error("Could not copy the link")
	}
}

const endsAt = computed(() => {
	if (!props.event) return ""
	if (laterEndDate.value) {
		const date = dayjs(laterEndDate.value).format("ddd, D MMM")
		const time = props.event.end_time ? `, ${timeLabel12Hour(props.event.end_time)}` : ""
		return `to ${date}${time}`
	}
	if (!props.event.start_time) return "Time to be announced"
	const start = timeLabel12Hour(props.event.start_time)
	return props.event.end_time ? `${start} – ${timeLabel12Hour(props.event.end_time)}` : start
})
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="lg">
			<template v-if="event">
				<div class="flex gap-2 p-2">
					<DrawerClose as-child>
						<Button size="sm" icon="lucide-chevrons-right" aria-label="Close" />
					</DrawerClose>

					<!-- Both need a route: an unpublished event has no public page to point at. -->
					<template v-if="event.route">
						<Button size="sm" label="Copy Link" icon-left="lucide-copy" @click="copyLink" />
						<Button
							size="sm"
							label="Event Page"
							icon-right="lucide-arrow-up-right"
							:link="eventUrl(event.route)"
						/>
					</template>
				</div>
				<Alert
					v-if="event.is_host"
					class="shrink-0 rounded-none"
					theme="blue"
					title="You have manage access for this event."
					:primary-action="{
						label: 'Manage',
						route: `/manage/events/${event.name}`,
						variant: 'outline',
						theme: 'blue',
						size: 'sm',
					}"
				/>

				<div class="flex-1 overflow-y-auto">
					<div class="relative p-4">
						<img
							v-if="event.banner_image"
							class="aspect-video w-full rounded-6 object-cover border"
							:src="event.banner_image"
							:style="banner"
							alt=""
						/>
						<div v-else class="aspect-video w-full rounded-6 border" :style="banner" />

						<EventCountdownPill
							:event="event"
							class="absolute bottom-5 left-1/2 -translate-x-1/2 translate-y-1/2"
						/>
					</div>

					<div class="flex flex-col gap-2 px-4">
						<DrawerTitle class="text-6xl font-semibold text-ink-gray-9">
							{{ event.title }}
						</DrawerTitle>

						<div v-if="event.team_name" class="flex items-center gap-2">
							<Avatar :image="event.team_logo || undefined" :label="event.team_name" size="sm" />
							<span class="text-base text-ink-gray-6">By {{ event.team_name }}</span>
						</div>
					</div>

					<div class="flex flex-col gap-4 p-4">
						<div class="flex items-center gap-3">
							<div
								class="flex size-11 shrink-0 flex-col items-center justify-center rounded-5 border border-outline-gray-2 leading-none"
							>
								<span class="text-xs text-ink-gray-5">{{ day.month }}</span>
								<span class="text-base font-semibold text-ink-gray-8">{{ day.date }}</span>
							</div>
							<div class="space-y-0.5">
								<!-- Doubles as the drawer's accessible description. -->
								<DrawerDescription class="text-base font-medium text-ink-gray-8">
									{{ startsAt }}
								</DrawerDescription>
								<p class="text-base text-ink-gray-5">{{ endsAt }}</p>
							</div>
						</div>

						<div class="flex items-center gap-3">
							<div
								class="flex size-11 shrink-0 items-center justify-center rounded-5 border border-outline-gray-2"
							>
								<Icon
									:name="event.venue ? 'lucide-map-pin' : 'lucide-map-pin-off'"
									class="size-5 text-ink-gray-6"
								/>
							</div>
							<p class="text-base text-ink-gray-8">
								{{ event.venue || "Venue to be announced" }}
							</p>
						</div>
					</div>

					<EventMyTickets :event="event" class="mx-4 mb-4" />
				</div>
			</template>
		</DrawerContent>
	</Drawer>
</template>
