<script setup lang="ts">
import { computed } from "vue"

import { colorClasses, colorStyle } from "./scheduleColors"
import { scheduleIcon } from "./scheduleIcons"
import { clockLabel, endMinutes, startMinutes, toTime } from "./scheduleTime"
import type { ScheduleItem, ScheduleItemType } from "./scheduleTypes"

const props = defineProps<{ item: ScheduleItem; type?: ScheduleItemType; conflict: boolean }>()
defineEmits<{ select: [] }>()

const time = computed(
	() => `${clockLabel(props.item.start_time)} – ${clockLabel(toTime(endMinutes(props.item)))}`,
)
const short = computed(() => endMinutes(props.item) - startMinutes(props.item) <= 30)
</script>

<template>
	<button
		type="button"
		draggable="false"
		class="flex size-full flex-col items-start gap-0.5 overflow-hidden rounded-4 border px-2 py-1 text-left transition-[transform,box-shadow] duration-150 ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4 active:scale-[0.99]"
		:class="[colorClasses(type?.color), conflict && 'ring-1 ring-outline-red-3']"
		:style="colorStyle(type?.color)"
		@click.stop="$emit('select')"
	>
		<span class="flex w-full items-center gap-1.5 text-p-sm font-semibold leading-tight">
			<span :class="[scheduleIcon(type?.icon), 'size-3.5 shrink-0']" aria-hidden="true" />
			<span class="min-w-0 flex-1" :class="short ? 'truncate' : 'line-clamp-2'">{{
				item.title
			}}</span>
			<span
				v-if="conflict"
				class="lucide-triangle-alert size-3.5 shrink-0 text-ink-red-6"
				role="img"
				aria-label="Overlaps another item"
			/>
		</span>
		<span v-if="!short" class="text-p-xs opacity-80">{{ time }}</span>
	</button>
</template>
