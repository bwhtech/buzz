<script setup lang="ts">
import { Alert, ErrorMessage } from "frappe-ui"
import { computed } from "vue"

const props = defineProps<{
	// What is enabled, as the title reads it: "Ticket type", "Add-on".
	noun: string
	enabled: boolean
	editable: boolean
	loading?: boolean
	error?: string
}>()
const emit = defineEmits<{ toggle: [] }>()

const alert = computed(() =>
	props.enabled
		? { theme: "green" as const, title: `${props.noun} is Enabled`, action: "Disable" }
		: { theme: "amber" as const, title: `${props.noun} is Disabled`, action: "Enable" },
)
</script>

<template>
	<div>
		<Alert
			:theme="alert.theme"
			:title="alert.title"
			:primary-action="
				editable
					? {
							label: alert.action,
							variant: 'outline',
							theme: 'gray',
							loading,
							onClick: () => emit('toggle'),
						}
					: undefined
			"
		/>
		<ErrorMessage class="mt-2" :message="error" />
	</div>
</template>
