<script setup lang="ts">
import { Button, FormControl } from "frappe-ui"
import { computed, ref } from "vue"

import type { LocationPicker } from "@/components/dashboard/events/location/useLocationPicker"

const props = defineProps<{ picker: LocationPicker; suggestedName?: string }>()
const emit = defineEmits<{ saved: [venue: string]; cancel: [] }>()

const venueName = ref(props.suggestedName ?? "")
const address = ref("")
const isSaving = ref(false)
const isIncomplete = computed(() => !venueName.value.trim() || !address.value.trim())

async function save() {
	isSaving.value = true
	const name = await props.picker.saveManually(venueName.value.trim(), address.value.trim())
	isSaving.value = false
	if (name) emit("saved", name)
}
</script>

<template>
	<form novalidate class="flex flex-col gap-4" @submit.prevent="save">
		<FormControl
			v-model="venueName"
			label="Name"
			placeholder="Nehru Centre Auditorium"
			autocomplete="off"
		/>
		<FormControl
			v-model="address"
			type="textarea"
			label="Address or map link"
			placeholder="Paste a Google Maps link, or type the address"
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
