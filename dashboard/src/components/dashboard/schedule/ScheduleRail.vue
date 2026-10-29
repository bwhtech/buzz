<script setup lang="ts">
import { TabButtons } from "frappe-ui"
import { computed } from "vue"

import ScheduleCustomLibrary from "./ScheduleCustomLibrary.vue"
import ScheduleInspector from "./ScheduleInspector.vue"
import ScheduleTalkLibrary from "./ScheduleTalkLibrary.vue"
import { useBoard, useBuilder } from "./useScheduleBoard"

const builder = useBuilder()
const board = useBoard()

const unscheduledCount = computed(
	() =>
		builder.talks.value.filter(
			(talk) => !builder.items.value.some((item) => item.talk === talk.name),
		).length,
)
const tabs = computed(() => [
	{ label: `Talks · ${unscheduledCount.value}`, value: "talks" },
	{ label: "Custom items", value: "custom" },
])
const dropping = computed(() => board.dragging.value && !!board.dragKey.value)
</script>

<template>
	<aside
		class="relative flex min-h-0 w-80 shrink-0 flex-col border-l border-outline-gray-1 bg-surface-base"
		@dragover="board.panelOver($event)"
		@drop="board.panelDropped($event)"
		@dragleave="board.panelLeave($event)"
	>
		<ScheduleInspector v-if="board.selected.value" :item="board.selected.value" />
		<template v-else>
			<div class="px-3 pb-2 pt-3">
				<TabButtons v-model="board.tab.value" :options="tabs" />
			</div>
			<ScheduleTalkLibrary v-if="board.tab.value === 'talks'" />
			<ScheduleCustomLibrary v-else />
		</template>
		<div
			v-if="dropping"
			class="pointer-events-none absolute inset-2 z-10 flex items-center justify-center gap-2 rounded-5 border-[1.5px] border-dashed text-p-sm font-semibold transition-colors"
			:class="
				board.panelDrop.value
					? 'border-outline-blue-3 bg-surface-blue-1 text-ink-blue-7'
					: 'border-outline-gray-3 bg-surface-gray-1 text-ink-gray-6'
			"
		>
			<span class="lucide-undo-2 size-4" aria-hidden="true" />
			Drop to unschedule
		</div>
	</aside>
</template>
