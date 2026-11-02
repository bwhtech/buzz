<script setup lang="ts">
import { Button, Dialog, FormControl } from "frappe-ui"
import { ref, watch } from "vue"

import type { ScheduleDay } from "./scheduleTypes"

const open = defineModel<boolean>({ required: true })
const props = defineProps<{ day: ScheduleDay | null; taken: string[] }>()
const emit = defineEmits<{ save: [day: ScheduleDay] }>()

const label = ref("")
const date = ref("")
watch(open, (isOpen) => {
	if (!isOpen || !props.day) return
	label.value = props.day.label
	date.value = props.day.date
})

const clash = () => date.value !== props.day?.date && props.taken.includes(date.value)
const invalid = () => !date.value || clash()

function submit() {
	if (invalid()) return
	emit("save", { date: date.value, label: label.value.trim() })
	open.value = false
}
</script>

<template>
	<Dialog v-model="open" title="Edit day">
		<form novalidate class="space-y-4" @submit.prevent="submit">
			<FormControl v-model="label" label="Label" placeholder="Day 1" autocomplete="off" />
			<FormControl
				v-model="date"
				type="date"
				label="Date"
				:description="clash() ? 'Another day already uses this date.' : undefined"
			/>
			<Button
				type="button"
				variant="solid"
				label="Save"
				class="w-full"
				:disabled="invalid()"
				@click="submit"
			/>
		</form>
	</Dialog>
</template>
