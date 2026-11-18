<script setup lang="ts">
import { useDebounceFn } from "@vueuse/core"
import { nextTick, onMounted, useTemplateRef, watch } from "vue"

// One wheel column: rows snap to the centre band, the edges fade, and whatever settles in
// the band is the value.
const props = defineProps<{ items: { value: string; label: string }[]; label: string }>()
const value = defineModel<string>({ required: true })

const ROW_HEIGHT = 34
const VISIBLE_ROWS = 5
const scroller = useTemplateRef<HTMLElement>("scroller")

function scrollTo(target: string, smooth: boolean) {
	const index = props.items.findIndex((item) => item.value === target)
	if (index < 0 || !scroller.value) return
	scroller.value.scrollTo({ top: index * ROW_HEIGHT, behavior: smooth ? "smooth" : "auto" })
}

const settle = useDebounceFn(() => {
	if (!scroller.value) return
	const item = props.items[Math.round(scroller.value.scrollTop / ROW_HEIGHT)]
	if (item && item.value !== value.value) value.value = item.value
}, 120)

onMounted(() => nextTick().then(() => scrollTo(value.value, false)))
watch(value, (next) => nextTick().then(() => scrollTo(next, false)))
</script>

<template>
	<div
		ref="scroller"
		class="wheel overflow-y-auto overscroll-contain"
		role="listbox"
		:aria-label="label"
		:style="{
			height: `${ROW_HEIGHT * VISIBLE_ROWS}px`,
			paddingBlock: `${(ROW_HEIGHT * (VISIBLE_ROWS - 1)) / 2}px`,
		}"
		@scroll="settle"
	>
		<button
			v-for="item in items"
			:key="item.value"
			type="button"
			role="option"
			tabindex="-1"
			class="row flex w-full snap-center items-center justify-center text-lg tabular-nums"
			:style="{ height: `${ROW_HEIGHT}px` }"
			:aria-selected="item.value === value"
			@click="scrollTo(item.value, true)"
		>
			{{ item.label }}
		</button>
	</div>
</template>

<style scoped>
.wheel {
	scroll-snap-type: y mandatory;
	scrollbar-width: none;
	-webkit-mask-image: linear-gradient(to bottom, transparent, #000 35%, #000 65%, transparent);
	mask-image: linear-gradient(to bottom, transparent, #000 35%, #000 65%, transparent);
}
.wheel::-webkit-scrollbar {
	display: none;
}
.row {
	color: var(--ink-gray-5);
}
.row[aria-selected="true"] {
	color: var(--ink-gray-9);
	font-weight: 500;
}
</style>
