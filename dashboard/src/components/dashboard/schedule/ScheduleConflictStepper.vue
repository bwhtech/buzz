<script setup lang="ts">
import { computed } from "vue"

import { useBoard, useBuilder } from "./useScheduleBoard"

const props = defineProps<{ size?: "md" | "lg" }>()
const builder = useBuilder()
const board = useBoard()

const total = computed(() => builder.conflictedItems.value.length)
const index = computed(() =>
	builder.conflictedItems.value.findIndex((item) => item.key === board.selectedKey.value),
)
const large = computed(() => props.size === "lg")
const label = computed(() => {
	if (index.value === -1) return `${total.value} ${total.value === 1 ? "conflict" : "conflicts"}`
	return `${index.value + 1} of ${total.value}${large.value ? "" : " conflicts"}`
})
// Touch screens keep :hover after a tap, so the large size only tints while pressed.
const pressClass = computed(() =>
	large.value ? "active:bg-surface-red-2" : "hover:bg-surface-red-2",
)
const arrowClass = computed(() => [
	"grid h-full place-items-center",
	pressClass.value,
	large.value ? "w-10" : "w-6",
])
</script>

<template>
	<div
		v-if="total"
		class="flex shrink-0 items-center overflow-hidden bg-surface-red-1 text-ink-red-7"
		:class="large ? 'h-10 rounded-full text-p-base shadow-xl' : 'h-7 rounded-4 text-p-sm'"
	>
		<button
			type="button"
			class="flex h-full items-center gap-1.5 tabular-nums"
			:class="[pressClass, large ? 'pl-4 pr-2' : 'px-2']"
			@click="board.stepConflict(1)"
		>
			<span class="lucide-triangle-alert size-3.5" aria-hidden="true" />{{ label }}
		</button>
		<button
			type="button"
			:class="arrowClass"
			aria-label="Previous conflict"
			title="Previous conflict"
			@click="board.stepConflict(-1)"
		>
			<span class="lucide-chevron-up size-4" aria-hidden="true" />
		</button>
		<button
			type="button"
			:class="[arrowClass, large && 'pr-1']"
			aria-label="Next conflict"
			title="Next conflict"
			@click="board.stepConflict(1)"
		>
			<span class="lucide-chevron-down size-4" aria-hidden="true" />
		</button>
	</div>
</template>
