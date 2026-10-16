<template>
	<div
		v-if="secondsLeft !== null"
		class="flex items-center justify-between gap-3 rounded-6 bg-surface-gray-2 px-3 py-2 text-p-sm text-ink-gray-7"
	>
		<span v-if="expired">{{
			__("Your hold has expired. These tickets may go to someone else.")
		}}</span>
		<span v-else>
			{{ __("Your tickets are held for") }}
			<span class="font-medium tabular-nums text-ink-gray-9">{{ clock }}</span>
		</span>
		<Button v-if="expired" size="sm" @click="emit('holdAgain')">{{ __("Hold again") }}</Button>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed } from "vue"

import { formatCountdown } from "@/utils/eventDates"

const props = defineProps<{ secondsLeft: number | null; expired: boolean }>()
const emit = defineEmits<{ holdAgain: [] }>()

const clock = computed(() => formatCountdown(props.secondsLeft ?? 0))
</script>
