<script setup lang="ts">
import { Button, Dialog, FormControl, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { createVenue } from "@/data/venues"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ team: string }>()
const isOpen = defineModel<boolean>({ required: true })
// The name the picker was searching for when it gave up and offered to add one.
const suggestedName = defineModel<string>("suggestedName", { default: "" })
const emit = defineEmits<{ created: [venue: string] }>()

const name = ref("")
const address = ref("")
const showErrors = ref(false)

const errorMessage = ref("")

watch(isOpen, (open) => {
	if (!open) return
	name.value = suggestedName.value
	address.value = ""
	showErrors.value = false
	errorMessage.value = ""
})

const invalid = computed(() => !name.value.trim() || !address.value.trim())

async function submit() {
	showErrors.value = true
	if (invalid.value) return

	errorMessage.value = ""
	const venue = await createVenue
		.submit({
			team: props.team,
			venue_name: name.value.trim(),
			address: address.value.trim(),
		})
		.catch((error) => {
			errorMessage.value = serverErrorMessage(error)
			return null
		})
	if (!venue) return

	toast.success(`${venue.venue_name} added`)
	emit("created", venue.name)
	isOpen.value = false
}
</script>

<template>
	<Dialog v-model="isOpen" title="Add venue">
		<form novalidate class="space-y-4" @submit.prevent="submit">
			<FormControl
				v-model="name"
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

			<ErrorMessage
				:message="showErrors && invalid ? 'A venue needs a name and an address.' : errorMessage"
			/>

			<!-- type=button: inside a form, a submit button would run `submit` twice —
				 once on click, once on the form's own submit — and the second insert
				 collides with the venue the first one just created. -->
			<Button
				type="button"
				variant="solid"
				label="Add venue"
				class="w-full"
				:loading="createVenue.loading"
				@click="submit"
			/>
		</form>
	</Dialog>
</template>
