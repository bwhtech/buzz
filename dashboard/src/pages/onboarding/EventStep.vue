<script setup lang="ts">
import { ErrorMessage, TabButtons, TextInput } from "frappe-ui"
import { computed } from "vue"

import EventCard from "./EventCard.vue"
import { type Medium, eventError, flow, saveFirstEvent } from "./useOnboarding"

const event = flow.event
const mediums = computed<{ value: Medium; label: string }[]>(() => [
	{ value: "Online", label: __("Online") },
	{ value: "In Person", label: __("Venue") },
])

defineExpose({
	canContinue: () => Boolean(event.title.trim() && event.start_date && event.start_time),
	save: saveFirstEvent,
})
</script>

<template>
	<div class="flex flex-col gap-4">
		<TextInput
			v-model="event.title"
			:label="__('Event title')"
			:placeholder="__('JS Hack Night #12')"
			autofocus
		/>
		<div class="grid grid-cols-2 gap-3">
			<TextInput v-model="event.start_date" type="date" :label="__('Date')" />
			<TextInput v-model="event.start_time" type="time" :label="__('Start time')" />
		</div>
		<div class="flex flex-col gap-1.5">
			<p class="text-xs text-ink-gray-5">{{ __("Where") }}</p>
			<TabButtons v-model="event.medium" :options="mediums" fluid />
		</div>
		<TextInput
			v-if="event.medium === 'In Person'"
			v-model="event.venue_name"
			:placeholder="__('Venue name or address')"
		/>
		<p v-else class="text-sm text-ink-gray-5">
			{{ __("Add the meeting link later from the event page.") }}
		</p>
		<ErrorMessage :message="eventError" />
		<div class="lg:hidden">
			<EventCard />
		</div>
	</div>
</template>
