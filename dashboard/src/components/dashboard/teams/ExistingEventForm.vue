<script setup lang="ts">
import { Button, ErrorMessage, FormControl, dayjs, toast, useCall } from "frappe-ui"
import { nextTick, ref, watch } from "vue"

import { serverErrorMessage } from "@/utils/serverError"

interface EventOption {
	name: string
	title: string
	start_date: string
	team_name: string
}

const props = defineProps<{ community: string; canReview?: boolean }>()
const emit = defineEmits<{ added: []; external: [url: string] }>()

const METHOD = "/api/v2/method/buzz.api.communities"
const findEvent = useCall<EventOption, { url: string }>({
	url: `${METHOD}.find_event`,
	immediate: false,
})
// An organizer lists the event straight away; anyone else sends it for review.
const addEvent = useCall<null, { community: string; event: string }>({
	url: `${METHOD}.${props.canReview ? "add_event" : "submit_event"}`,
	method: "POST",
	immediate: false,
})

const url = ref("")
const event = ref<EventOption | null>(null)
watch(url, () => (event.value = null))

async function lookUpEvent() {
	if (!url.value.trim() || event.value) return
	event.value = await findEvent.submit({ url: url.value.trim() }).catch(() => null)
}

async function submit() {
	if (!event.value) return
	// useCall does not reject on a server error; it sets `error`.
	await addEvent.submit({ community: props.community, event: event.value.name })
	if (addEvent.error) return toast.error(serverErrorMessage(addEvent.error))
	toast.success(
		props.canReview ? __("Event added to your calendar") : __("Event submitted for review"),
	)
	emit("added")
}
</script>

<template>
	<form class="space-y-4" @submit.prevent="lookUpEvent">
		<FormControl
			v-model="url"
			type="url"
			:label="__('Event link')"
			:placeholder="__('Enter Buzz Event URL')"
			autofocus
			@paste="nextTick(lookUpEvent)"
			@blur="lookUpEvent"
		/>

		<div v-if="findEvent.error && !event" class="space-y-2">
			<ErrorMessage :message="serverErrorMessage(findEvent.error)" />
			<Button
				variant="ghost"
				icon-left="lucide-link"
				:label="
					canReview
						? __('Add it as an external event instead')
						: __('Submit it as an external event instead')
				"
				@click="emit('external', url.trim())"
			/>
		</div>

		<div v-if="event" class="space-y-1 rounded-6 border border-outline-gray-2 p-3">
			<p class="text-base font-semibold text-ink-gray-9">{{ event.title }}</p>
			<p class="text-sm text-ink-gray-6">
				{{ dayjs(event.start_date).format("ddd D MMM YYYY") }} · {{ event.team_name }}
			</p>
		</div>

		<div class="flex justify-end">
			<Button
				variant="solid"
				:label="canReview ? __('Add to Calendar') : __('Submit for Review')"
				:disabled="!event"
				:loading="addEvent.loading || findEvent.loading"
				@click="submit"
			/>
		</div>
	</form>
</template>
