<script setup lang="ts">
import { useDebounceFn } from "@vueuse/core"
import { TextInput } from "frappe-ui"
import { computed, nextTick, onMounted, ref, useTemplateRef, watch } from "vue"

import { TIME_SLOTS, formatDuration, formatTime, minutesOf, parseTime } from "./scheduleTime"

// An iOS-style wheel: rows snap to a centre band, the edges blur away, and whatever
// settles in the band is the value. A typed time that is off the half-hour grid joins
// the wheel as its own row, so arbitrary times are first-class.
const props = withDefaults(defineProps<{ after?: string; label?: string }>(), {
	after: "",
	label: "",
})
const rowHeight = 36
const visibleRows = 6
const time = defineModel<string>({ default: "" })

const scroller = useTemplateRef<HTMLElement>("scroller")
const height = rowHeight * visibleRows
const pad = (height - rowHeight) / 2

const slots = computed(() => {
	const all = new Set(TIME_SLOTS)
	if (time.value) all.add(time.value)
	return [...all].toSorted((a, b) => minutesOf(a) - minutesOf(b))
})

const isBlocked = (slot: string) =>
	Boolean(props.after) && minutesOf(slot) <= minutesOf(props.after)
const lengthOf = (slot: string) =>
	props.after && !isBlocked(slot) ? formatDuration(minutesOf(slot) - minutesOf(props.after)) : ""

const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches

function scrollToSlot(slot: string, smooth: boolean) {
	const index = slots.value.indexOf(slot)
	if (index < 0 || !scroller.value) return
	scroller.value.scrollTo({
		top: index * rowHeight,
		behavior: smooth && !reduceMotion() ? "smooth" : "auto",
	})
}

function nearestOpen(index: number) {
	for (let distance = 0; distance < slots.value.length; distance++) {
		for (const candidate of [index + distance, index - distance]) {
			const slot = slots.value[candidate]
			if (slot && !isBlocked(slot)) return slot
		}
	}
	return ""
}

// Whatever rests in the band once scrolling stops becomes the value.
const settle = useDebounceFn(() => {
	if (!scroller.value) return
	const index = Math.round(scroller.value.scrollTop / rowHeight)
	const slot = nearestOpen(index)
	if (!slot) return
	if (slot !== slots.value[index]) scrollToSlot(slot, true)
	if (slot !== time.value) time.value = slot
}, 140)

function step(by: number) {
	const index = slots.value.indexOf(time.value) + by
	const slot = slots.value[index]
	if (slot && !isBlocked(slot)) {
		time.value = slot
		scrollToSlot(slot, false)
	}
}

onMounted(() => nextTick().then(() => scrollToSlot(time.value, false)))
watch(time, (slot) => nextTick().then(() => scrollToSlot(slot, false)))
watch(
	() => props.after,
	() => isBlocked(time.value) && settle(),
)

const typedText = ref("")
const typedError = ref("")

function commitTyped() {
	if (!typedText.value.trim()) return
	const parsed = parseTime(typedText.value)
	if (!parsed) return (typedError.value = __("Try 7:45pm or 19:45"))
	if (isBlocked(parsed)) return (typedError.value = __("Ends after {0}", [formatTime(props.after)]))
	typedError.value = ""
	typedText.value = ""
	time.value = parsed
}
</script>

<template>
	<div class="flex min-w-0 flex-col gap-1.5">
		<p v-if="label" class="flex h-7 items-center px-1 text-sm font-medium text-ink-gray-9">
			{{ label }}
		</p>
		<TextInput
			v-model="typedText"
			type="text"
			inputmode="text"
			:placeholder="__('Type a time')"
			:aria-label="`${label || 'Time'}: type any time`"
			@keydown.enter.prevent="commitTyped"
			@blur="commitTyped"
			@input="typedError = ''"
		/>
		<p v-if="typedError" role="alert" class="px-1 text-xs text-ink-red-7">{{ typedError }}</p>
		<div class="wheel relative" :style="{ height: `${height}px` }">
			<span
				class="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 rounded-4 bg-surface-gray-2"
				:style="{ height: `${rowHeight}px` }"
				aria-hidden="true"
			/>
			<div
				ref="scroller"
				class="wheel-scroller relative h-full overflow-y-auto overscroll-contain"
				role="listbox"
				tabindex="0"
				:aria-label="`${label || 'Time'} options`"
				:style="{ paddingBlock: `${pad}px`, scrollPaddingBlock: `${pad}px` }"
				@scroll="settle"
				@keydown.up.prevent="step(-1)"
				@keydown.down.prevent="step(1)"
			>
				<button
					v-for="slot in slots"
					:key="slot"
					type="button"
					role="option"
					tabindex="-1"
					class="wheel-row flex w-full snap-center items-center justify-between gap-2 px-3 text-sm tabular-nums"
					:style="{ height: `${rowHeight}px` }"
					:aria-selected="slot === time"
					:aria-disabled="isBlocked(slot) || undefined"
					@click="!isBlocked(slot) && scrollToSlot(slot, true)"
				>
					<span>{{ formatTime(slot) }}</span>
					<span class="text-xs text-ink-gray-5">{{ lengthOf(slot) }}</span>
				</button>
			</div>
			<span class="wheel-edge wheel-edge-top" aria-hidden="true" />
			<span class="wheel-edge wheel-edge-bottom" aria-hidden="true" />
		</div>
	</div>
</template>

<style scoped>
.wheel-scroller {
	scroll-snap-type: y mandatory;
	scrollbar-width: none;
}
.wheel-scroller::-webkit-scrollbar {
	display: none;
}
.wheel-scroller:focus-visible {
	outline: 2px solid var(--outline-gray-3);
	outline-offset: 2px;
	border-radius: 8px;
}
.wheel-row {
	color: var(--ink-gray-6);
	transition: color 120ms ease;
}
.wheel-row[aria-selected="true"] {
	color: var(--ink-gray-9);
	font-weight: 600;
}
.wheel-row[aria-disabled] {
	color: var(--ink-gray-3);
	cursor: default;
}
/* The iOS edge: rows fade out toward the top and bottom, with only a hint of blur
   on the outermost rows so the text near the band stays crisp. */
.wheel-scroller {
	-webkit-mask-image: linear-gradient(to bottom, transparent, #000 32%, #000 68%, transparent);
	mask-image: linear-gradient(to bottom, transparent, #000 32%, #000 68%, transparent);
}
.wheel-edge {
	position: absolute;
	left: 0;
	right: 0;
	height: 28%;
	pointer-events: none;
	-webkit-backdrop-filter: blur(0.75px);
	backdrop-filter: blur(0.75px);
}
.wheel-edge-top {
	top: 0;
	-webkit-mask-image: linear-gradient(to bottom, #000, transparent);
	mask-image: linear-gradient(to bottom, #000, transparent);
}
.wheel-edge-bottom {
	bottom: 0;
	-webkit-mask-image: linear-gradient(to top, #000, transparent);
	mask-image: linear-gradient(to top, #000, transparent);
}
</style>
