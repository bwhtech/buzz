<script setup lang="ts">
import { Button, FormControl, Tooltip } from "frappe-ui"
import { computed, ref } from "vue"

import type { LocationPicker } from "@/components/dashboard/events/location/useLocationPicker"
import { type MapLinkLocation, useMapLinkLocation } from "@/data/venues"

const props = defineProps<{ picker: LocationPicker; suggestedName?: string }>()
const emit = defineEmits<{
	saved: [venue: string]
	cancel: []
	locating: []
	located: [location: MapLinkLocation | null, venueName: string]
}>()

const mapLink = ref("")
const venueName = ref(props.suggestedName ?? "")
const address = ref("")
const isSaving = ref(false)
// Whether a link alone is enough is for the server to say: only it can read the location.
const isIncomplete = computed(
	() => !venueName.value.trim() || !(address.value.trim() || mapLink.value.trim()),
)

const mapLinkLocation = useMapLinkLocation()
let locatedLink = ""

// On leaving the field, so a link is read once it is whole and not on every keystroke.
async function locate() {
	const link = mapLink.value.trim()
	if (link === locatedLink) return
	locatedLink = link
	if (link) emit("locating")
	const location = link ? await mapLinkLocation.submit({ link }).catch(() => null) : null
	// Only into empty fields: what the organiser typed is never replaced.
	if (location?.name && !venueName.value.trim()) venueName.value = location.name
	if (location?.address && !address.value.trim()) address.value = location.address
	emit("located", location, venueName.value.trim())
}

async function save() {
	isSaving.value = true
	const name = await props.picker.saveManually({
		venue_name: venueName.value.trim(),
		address: address.value.trim(),
		map_link: mapLink.value.trim(),
	})
	isSaving.value = false
	if (name) emit("saved", name)
}
</script>

<template>
	<form novalidate class="flex flex-col gap-4" @submit.prevent="save">
		<FormControl
			v-model="mapLink"
			label="Map link"
			placeholder="Paste a Google Maps or OpenStreetMap link"
			autocomplete="off"
			@blur="locate"
		/>
		<!-- Locked while the link is read, so a name filled in from the link cannot land on
		 top of one being typed. The wrapper is the tooltip's trigger: a disabled input
		 takes no pointer events. -->
		<Tooltip text="Fetching the location from the map link…" :disabled="!mapLinkLocation.loading">
			<div>
				<FormControl
					v-model="venueName"
					label="Name"
					placeholder="Nehru Centre Auditorium"
					autocomplete="off"
					:disabled="mapLinkLocation.loading"
				/>
			</div>
		</Tooltip>
		<FormControl
			v-model="address"
			type="textarea"
			label="Address"
			placeholder="Optional when the map link shows the place"
		/>
		<ErrorMessage :message="picker.error" />
		<div class="mt-auto flex justify-end gap-2">
			<Button type="button" label="Back" @click="$emit('cancel')" />
			<Button
				type="submit"
				variant="solid"
				label="Add venue"
				:disabled="isIncomplete"
				:loading="isSaving"
			/>
		</div>
	</form>
</template>
