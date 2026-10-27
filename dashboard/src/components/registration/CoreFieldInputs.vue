<template>
	<template v-for="field in shownFields" :key="field.fieldname">
		<PhoneInput
			v-if="field.fieldname === 'buyer_phone'"
			v-model="model.buyer_phone"
			:class="widthClass(field)"
			:label="__(field.label)"
			:size="size"
			:error="phoneError || shown(field)"
			:required="required.includes(field.fieldname)"
		/>
		<FormControl
			v-else
			v-model="model[field.fieldname]"
			:class="widthClass(field)"
			:type="INPUTS[field.fieldname]?.type"
			:label="__(field.label)"
			:size="size"
			:error="shown(field)"
			:required="required.includes(field.fieldname)"
			:autocomplete="INPUTS[field.fieldname]?.autocomplete"
		/>
	</template>
</template>

<script setup lang="ts">
import { FormControl } from "frappe-ui"
import { computed } from "vue"

import PhoneInput from "../PhoneInput.vue"
import type { CoreField } from "./coreFields"

const props = defineProps<{
	fields: CoreField[]
	model: Record<string, any>
	errors: Record<string, string>
	showErrors: boolean
	size: "sm" | "lg"
	// Fields that must be answered; these show even when the organiser hid them.
	required: string[]
	phoneError?: string
}>()

const INPUTS: Record<string, { type?: "email"; autocomplete: string }> = {
	first_name: { autocomplete: "given-name" },
	last_name: { autocomplete: "family-name" },
	email: { type: "email", autocomplete: "email" },
	buyer_name: { autocomplete: "name" },
	buyer_email: { type: "email", autocomplete: "email" },
}

const shownFields = computed(() =>
	props.fields.filter((field) => field.enabled || props.required.includes(field.fieldname)),
)
const widthClass = (field: CoreField) => (field.width === "Full" ? "md:col-span-full" : "")
const shown = (field: CoreField) => (props.showErrors ? props.errors[field.fieldname] : undefined)
</script>
