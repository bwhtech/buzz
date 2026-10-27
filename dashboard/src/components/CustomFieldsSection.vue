<template>
	<div v-if="customFields.length > 0" class="space-y-4">
		<h5 v-if="showTitle" class="text-base-medium text-ink-gray-8 border-b pb-2">
			{{ __(title) || __("Additional Information") }}
		</h5>

		<FormGrid :fields="customFields" v-slot="{ field }">
			<CustomFieldInput
				:field="field"
				:model-value="getFieldValue(field.fieldname)"
				@update:model-value="updateFieldValue(field.fieldname, $event)"
			/>
		</FormGrid>
	</div>
</template>

<script setup lang="ts">
import { type PropType } from "vue"

import FormGrid from "@/components/FormGrid.vue"
import { type FrappeField, getFieldDefaultValue } from "@/composables/useCustomFields"

import CustomFieldInput from "./CustomFieldInput.vue"

const props = defineProps({
	customFields: {
		type: Array as PropType<FrappeField[]>,
		default: () => [],
	},
	modelValue: {
		type: Object as PropType<Record<string, any>>,
		default: () => ({}),
	},
	title: {
		type: String,
		default: "",
	},
	showTitle: {
		type: Boolean,
		default: true,
	},
})

const emit = defineEmits(["update:modelValue"])

// Get field value from model
const getFieldValue = (fieldname: string) => {
	const currentValue = props.modelValue[fieldname]

	// If field already has a value, return it
	if (currentValue !== undefined && currentValue !== null && currentValue !== "") {
		return currentValue
	}

	// Apply default value if available
	const field = props.customFields.find((f) => f.fieldname === fieldname)
	if (field) {
		const defaultValue = getFieldDefaultValue(field)
		if (defaultValue) {
			updateFieldValue(fieldname, defaultValue)
			return defaultValue
		}
	}

	return ""
}

// Update field value in model
const updateFieldValue = (fieldname: string, value: any) => {
	const updatedValue = { ...props.modelValue, [fieldname]: value }
	emit("update:modelValue", updatedValue)
}
</script>
