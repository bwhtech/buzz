<script setup lang="ts">
import { Button, Dialog, FormControl, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { createVenue } from "@/data/venues"
import type { FrappeError } from "@/types"

const props = defineProps<{ team: string }>()
const isOpen = defineModel<boolean>({ required: true })
// The name the picker was searching for when it gave up and offered to add one.
const suggestedName = defineModel<string>("suggestedName", { default: "" })
const emit = defineEmits<{ created: [venue: string] }>()

const name = ref("")
const address = ref("")
const showErrors = ref(false)

// createResource types its error as {}, so the message needs narrowing.
const errorMessage = computed(() => (createVenue.error as FrappeError | null)?.message)

watch(isOpen, (open) => {
	if (!open) return
	name.value = suggestedName.value
	address.value = ""
	showErrors.value = false
	createVenue.error = null
})

const invalid = computed(() => !name.value.trim() || !address.value.trim())

async function submit() {
	showErrors.value = true
	if (invalid.value) return

	await createVenue.submit({
		team: props.team,
		name: name.value.trim(),
		address: address.value.trim(),
	})
	if (createVenue.error) return

	toast.success(`${name.value.trim()} added`)
	emit("created", name.value.trim())
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

			<p v-if="showErrors && invalid" class="text-sm text-ink-red-4">
				A venue needs a name and an address.
			</p>
			<ErrorMessage v-else-if="errorMessage" :message="errorMessage" />

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
