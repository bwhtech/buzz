<script setup lang="ts">
import { Button, Dropdown } from "frappe-ui"
import { ref } from "vue"

import AddEventDialog from "@/components/dashboard/teams/AddEventDialog.vue"
import {
	type AddEventForm,
	addEventOptions,
	createEventUrl,
} from "@/components/dashboard/teams/addEventOptions"

// The dashboard calendar renders this, and so does the public community page as an island.
const props = defineProps<{
	community: string
	canReview?: boolean
	isPublicPage?: boolean
	// The menu spans its trigger, for a trigger that is a full-width row.
	matchTriggerWidth?: boolean
}>()
defineEmits<{ added: [] }>()
const isMenuOpen = defineModel<boolean>("open", { default: false })

const formType = ref<AddEventForm | null>(null)

const options = addEventOptions(props.canReview).map((option) => ({
	label: option.label,
	icon: option.icon,
	onClick: () => {
		if (option.type === "create") return window.location.assign(createEventUrl())
		formType.value = option.type
	},
}))
const label = props.canReview ? __("Add Event") : __("Submit Event")
</script>

<template>
	<Dropdown
		v-model:open="isMenuOpen"
		:options="options"
		:align="matchTriggerWidth ? 'end' : 'start'"
		:match-trigger-width="matchTriggerWidth"
	>
		<slot>
			<!-- The public page keeps its own espresso button, so the island swaps in unnoticed. -->
			<button
				v-if="isPublicPage"
				type="button"
				class="es-button team-event-action"
				data-variant="subtle"
				data-size="md"
			>
				<span class="icon lucide-plus" aria-hidden="true" />{{ label }}
			</button>
			<Button v-else variant="subtle" icon-left="lucide-plus" :label="label" />
		</slot>
	</Dropdown>
	<AddEventDialog
		v-model:form-type="formType"
		:community="community"
		:can-review="canReview"
		@added="$emit('added')"
	/>
</template>
