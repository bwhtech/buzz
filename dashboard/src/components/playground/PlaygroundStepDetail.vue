<script setup lang="ts">
import { Button } from "frappe-ui"

import type { ChecklistStep } from "./checklist"

defineProps<{ step: ChecklistStep; loading: boolean }>()
const emit = defineEmits<{ go: [step: ChecklistStep] }>()

const personaLabels: Record<string, string> = {
	organizer: __("Organizer"),
	attendee: __("Attendee"),
	front_desk: __("Front desk"),
}
</script>

<template>
	<div class="flex flex-col gap-3">
		<div class="flex flex-col gap-1">
			<span class="text-base-semibold text-ink-gray-9">{{ step.title }}</span>
			<span class="text-p-sm text-ink-gray-6">{{ step.description }}</span>
		</div>
		<Button
			v-if="!step.locked"
			variant="solid"
			:loading="loading"
			:label="__('Open as {0}', [personaLabels[step.persona]])"
			icon-right="lucide-arrow-right"
			@click="emit('go', step)"
		/>
		<span v-else class="text-p-sm text-ink-gray-5">{{ __("Create an event first.") }}</span>
	</div>
</template>
