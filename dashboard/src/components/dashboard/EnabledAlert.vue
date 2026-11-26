<script setup lang="ts">
import { Alert, ErrorMessage, toast } from "frappe-ui"
import { computed, ref } from "vue"

import { serverErrorMessage } from "@/utils/serverError"

type SetValue = {
	submit: (values: Record<string, 0 | 1>) => Promise<unknown>
	error: unknown
	loading: boolean
}

type AlertTheme = "green" | "amber" | "gray" | "blue" | "red"

const props = defineProps<{
	// What is enabled, as the title reads it: "Ticket type", "Add-on".
	noun: string
	enabled: boolean
	editable: boolean
	// The check field the toggle writes, through the record's useDoc setValue.
	field: string
	setValue: SetValue
	// Replaces the enabled or disabled wording, for records with more states than on and off.
	status?: { theme: AlertTheme; title: string }
}>()
const emit = defineEmits<{ changed: [] }>()

const error = ref("")
const alert = computed(() => {
	const fallback = props.enabled
		? { theme: "green" as const, title: `${props.noun} is Enabled` }
		: { theme: "amber" as const, title: `${props.noun} is Disabled` }
	return { ...(props.status ?? fallback), action: props.enabled ? "Disable" : "Enable" }
})

async function toggle() {
	const enabling = !props.enabled
	error.value = ""
	await props.setValue.submit({ [props.field]: enabling ? 1 : 0 }).catch(() => null)
	if (props.setValue.error) {
		error.value = serverErrorMessage(props.setValue.error) || "Could not update it. Try again."
		return
	}
	toast.success(`${props.noun} ${enabling ? "enabled" : "disabled"}`)
	emit("changed")
}
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
							loading: setValue.loading,
							onClick: toggle,
						}
					: undefined
			"
		/>
		<ErrorMessage class="mt-2" :message="error" />
	</div>
</template>
