<script setup lang="ts">
import { clock } from "./scheduleLayout"
import type { Placeholder } from "./useScheduleBoard"

defineProps<{ placeholder: Placeholder }>()
</script>

<template>
	<div
		class="pointer-events-none absolute z-[5] box-border overflow-hidden whitespace-nowrap rounded-4 border-[1.5px] border-dashed border-outline-gray-4 bg-surface-gray-1 px-2 py-0.5 text-p-xs tabular-nums text-ink-gray-6"
	>
		{{ clock(placeholder.start) }} – {{ clock(placeholder.start + placeholder.duration) }}
	</div>
</template>
