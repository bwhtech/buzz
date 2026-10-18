<script setup lang="ts">
import { Button, ErrorMessage, Switch } from "frappe-ui"
import { computed } from "vue"

import { PRESSABLE } from "@/components/dashboard/events/QuickActionTile.vue"
import { setShowCountdown } from "@/data/events"
import { eventPath } from "@/utils/eventUrl"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ event: string; route: string | null }>()
const emit = defineEmits<{ changed: [] }>()

// Flipped before the save lands so the banner answers at once; a refused save flips it back.
const showCountdown = defineModel<boolean>("showCountdown", { required: true })

const errorMessage = computed(() => serverErrorMessage(setShowCountdown.error))

async function toggle(show: boolean) {
	showCountdown.value = show
	await setShowCountdown
		.submit({ name: props.event, show_countdown: show ? 1 : 0 })
		.catch(() => null)
	if (setShowCountdown.error) showCountdown.value = !show
	else emit("changed")
}
</script>

<template>
	<h3 class="text-p-sm font-medium text-ink-gray-5">Quick actions</h3>

	<Button
		v-if="route"
		:class="`w-full !justify-start ${PRESSABLE}`"
		variant="ghost"
		label="Go to event page"
		:href="eventPath(route)"
	>
		<template #prefix>
			<span class="lucide-arrow-up-right size-4" aria-hidden="true" />
		</template>
	</Button>

	<div class="rounded-4 p-1 bg-surface-gray-2">
		<Switch
			:model-value="showCountdown"
			label="Show event countdown"
			description="Shows the time until the event starts on the event page banner."
			padded
			:disabled="setShowCountdown.loading"
			@update:model-value="toggle"
		/>
	</div>
	<ErrorMessage v-if="errorMessage" :message="errorMessage" />
</template>
