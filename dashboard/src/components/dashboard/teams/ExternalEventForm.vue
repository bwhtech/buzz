<script setup lang="ts">
import { Button, Combobox, DateTimePicker, FormControl, toast, useCall } from "frappe-ui"
import type { ComboboxCustomOption } from "frappe-ui"
import { computed, reactive, ref } from "vue"

import { usePlaceSearch } from "@/data/venues"
import { serverErrorMessage } from "@/utils/serverError"

// How the pickers show a value; the model stays `YYYY-MM-DD HH:mm:ss`.
const DATE_TIME_FORMAT = "ddd, D MMM YYYY, h:mm a"

const props = defineProps<{ community: string; canReview?: boolean; url?: string }>()
const emit = defineEmits<{ added: [] }>()

const event = reactive({
	event_title: "",
	host: "",
	event_location: "",
	google_place_id: null as string | null,
	start_datetime: "",
	end_datetime: "",
	event_url: props.url ?? "",
})
const hasRequiredFields = computed(() =>
	Object.entries(event).every(([field, value]) => field === "google_place_id" || Boolean(value)),
)

const locationQuery = ref("")
const isLocationOpen = ref(false)
const placeSearch = usePlaceSearch(locationQuery, isLocationOpen)

// A site without Google place search, or a place Google does not know, takes the text as typed.
const typedLocationOption: ComboboxCustomOption = {
	type: "custom",
	key: "typed",
	label: __("Use as typed"),
	icon: "lucide-pencil",
	condition: ({ query }) => Boolean(query.trim()),
	onClick: ({ query }) =>
		Object.assign(event, { event_location: query.trim(), google_place_id: null }),
}
const locationOptions = computed(() => [
	...placeSearch.places.map((place) => ({
		label: place.name,
		value: place.place_id,
		description: place.address ?? "",
	})),
	typedLocationOption,
])

function selectPlace(placeId: unknown) {
	const place = placeSearch.places.find((option) => option.place_id === placeId)
	if (!place) return
	event.event_location = [place.name, place.address].filter(Boolean).join(", ")
	event.google_place_id = place.place_id
}

const addExternalEvent = useCall<null, { community: string; event: typeof event }>({
	url: `/api/v2/method/buzz.api.communities.${props.canReview ? "add" : "submit"}_external_event`,
	method: "POST",
	immediate: false,
})

async function submit() {
	// useCall does not reject on a server error; it sets `error`.
	await addExternalEvent.submit({ community: props.community, event })
	if (addExternalEvent.error) return toast.error(serverErrorMessage(addExternalEvent.error))
	toast.success(
		props.canReview ? __("Event added to your calendar") : __("Event submitted for review"),
	)
	emit("added")
}
</script>

<template>
	<form class="space-y-4" @submit.prevent="submit">
		<FormControl
			v-model="event.event_url"
			type="url"
			:label="__('Event link')"
			placeholder="https://lu.ma/some-event"
			required
			autofocus
		/>
		<FormControl v-model="event.event_title" :label="__('Event name')" required />
		<Combobox
			v-model:query="locationQuery"
			v-model:open="isLocationOpen"
			:model-value="event.google_place_id"
			:options="locationOptions"
			:filterable="false"
			:loading="placeSearch.isSearching"
			:label="__('Location')"
			required
			:placeholder="event.event_location || __('Search for a place')"
			@update:model-value="selectPlace"
		/>
		<FormControl v-model="event.host" :label="__('Hosted by')" required />
		<div class="grid grid-cols-2 gap-3">
			<DateTimePicker
				v-model="event.start_datetime"
				:label="__('Starts')"
				required
				:format="DATE_TIME_FORMAT"
			/>
			<DateTimePicker
				v-model="event.end_datetime"
				:label="__('Ends')"
				required
				:format="DATE_TIME_FORMAT"
				:min="event.start_datetime"
			/>
		</div>

		<div class="flex justify-end">
			<Button
				variant="solid"
				type="submit"
				:label="canReview ? __('Add to Calendar') : __('Submit for Review')"
				:disabled="!hasRequiredFields"
				:loading="addExternalEvent.loading"
			/>
		</div>
	</form>
</template>
