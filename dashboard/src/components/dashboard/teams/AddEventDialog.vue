<script setup lang="ts">
import { Dialog } from "frappe-ui"
import { computed, ref } from "vue"

import { type AddEventForm, addEventOptions } from "@/components/dashboard/teams/addEventOptions"
import ExistingEventForm from "@/components/dashboard/teams/ExistingEventForm.vue"
import ExternalEventForm from "@/components/dashboard/teams/ExternalEventForm.vue"

const props = defineProps<{ community: string; canReview?: boolean }>()
const emit = defineEmits<{ added: [] }>()
// The dialog is open while a form is chosen.
const formType = defineModel<AddEventForm | null>("formType", { default: null })

const isOpen = computed({
	get: () => Boolean(formType.value),
	set: (open) => !open && (formType.value = null),
})
const title = computed(() => {
	const option = addEventOptions(props.canReview).find((choice) => choice.type === formType.value)
	return option && ("dialogTitle" in option ? option.dialogTitle : option.label)
})

// A link that is not a Buzz event carries over into the external form.
const externalUrl = ref("")

function openExternalForm(url: string) {
	externalUrl.value = url
	formType.value = "external"
}

function onEventAdded() {
	formType.value = null
	emit("added")
}
</script>

<template>
	<Dialog v-model="isOpen" :title="title" size="lg">
		<ExistingEventForm
			v-if="formType === 'existing'"
			:community="community"
			:can-review="canReview"
			@added="onEventAdded"
			@external="openExternalForm"
		/>
		<ExternalEventForm
			v-else-if="formType === 'external'"
			:community="community"
			:can-review="canReview"
			:url="externalUrl"
			@added="onEventAdded"
		/>
	</Dialog>
</template>
