<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed, onBeforeUnmount, onMounted, ref } from "vue"

import { type ChecklistStep, SPOTLIGHT_KEY, useBrowserCompletedSteps } from "./checklist"

const CONTROLS = "button, a, input, textarea, [role=button], [role=tab]"
const FIND_TIMEOUT_MS = 10000

const step = ref<ChecklistStep>()
const box = ref<DOMRect>()
const hint = ref<HTMLElement>()
const completedSteps = useBrowserCompletedSteps()
let target: HTMLElement | undefined
let frame = 0

// innerText, not textContent: it keeps the break between a tile's title and its state.
function label(element: HTMLElement) {
	const text = element.getAttribute("aria-label") || (element as HTMLInputElement).placeholder
	return (text || element.innerText || "").replace(/\s+/g, " ").trim()
}

function findTarget(text: string) {
	return [...document.querySelectorAll<HTMLElement>(CONTROLS)].find(
		(element) =>
			element.offsetParent &&
			!element.closest("[data-playground]") &&
			label(element).startsWith(text),
	)
}

// The page renders after an API call, so look until the control shows up or time runs out.
function waitForTarget(text: string) {
	const startedAt = Date.now()
	const look = () => {
		target = findTarget(text)
		if (target) return show(target)
		if (Date.now() - startedAt < FIND_TIMEOUT_MS) frame = requestAnimationFrame(look)
		else dismiss()
	}
	look()
}

function show(element: HTMLElement) {
	element.scrollIntoView({ block: "center", behavior: "smooth" })
	const follow = () => {
		box.value = element.getBoundingClientRect()
		frame = requestAnimationFrame(follow)
	}
	follow()
}

function dismiss() {
	cancelAnimationFrame(frame)
	sessionStorage.removeItem(SPOTLIGHT_KEY)
	step.value = box.value = target = undefined
}

function onPointerDown(event: PointerEvent) {
	if (!step.value || hint.value?.contains(event.target as Node)) return
	if (step.value.completes_on === "click" && target?.contains(event.target as Node)) {
		completedSteps.add(step.value.name)
	}
	dismiss()
}

const onKeyDown = (event: KeyboardEvent) => event.key === "Escape" && dismiss()

onMounted(() => {
	const saved = sessionStorage.getItem(SPOTLIGHT_KEY)
	if (!saved) return
	step.value = JSON.parse(saved)
	if (step.value?.target) waitForTarget(step.value.target)
	document.addEventListener("pointerdown", onPointerDown, true)
	document.addEventListener("keydown", onKeyDown)
})

onBeforeUnmount(() => {
	cancelAnimationFrame(frame)
	document.removeEventListener("pointerdown", onPointerDown, true)
	document.removeEventListener("keydown", onKeyDown)
})

const PADDING = 6
const GAP = 12
const HINT_WIDTH = 256

const cutoutStyle = computed(() => {
	const rect = box.value!
	return {
		transform: `translate(${rect.left - PADDING}px, ${rect.top - PADDING}px)`,
		width: `${rect.width + PADDING * 2}px`,
		height: `${rect.height + PADDING * 2}px`,
	}
})

// Below the control when it fits, above it otherwise; right-aligned to it near the right edge.
const hintStyle = computed(() => {
	const rect = box.value!
	const height = hint.value?.offsetHeight ?? 120
	const fitsBelow = rect.bottom + PADDING + GAP + height < window.innerHeight
	const top = fitsBelow ? rect.bottom + PADDING + GAP : rect.top - PADDING - GAP - height
	const overflowsRight = rect.left + HINT_WIDTH > window.innerWidth - 16
	const left = Math.max(overflowsRight ? rect.right - HINT_WIDTH : rect.left, 16)
	return { top: `${top}px`, left: `${left}px`, width: `${HINT_WIDTH}px` }
})
</script>

<template>
	<template v-if="step && box">
		<!-- Pointer events pass through, so the highlighted control stays clickable. -->
		<div
			data-playground
			aria-hidden="true"
			class="spotlight-cutout pointer-events-none fixed left-0 top-0 z-40 rounded-lg"
			:style="cutoutStyle"
		/>
		<div
			ref="hint"
			data-playground
			role="status"
			class="spotlight-hint fixed z-[60] flex flex-col gap-3 rounded-5 border border-outline-gray-2 bg-surface-elevation-2 p-4 shadow-xl"
			:style="hintStyle"
		>
			<div class="flex flex-col gap-1">
				<span class="text-base-semibold text-ink-gray-9">{{ step.title }}</span>
				<span class="text-p-sm text-ink-gray-6">{{ step.description }}</span>
			</div>
			<Button class="self-start" :label="__('Got it')" @click="dismiss" />
		</div>
	</template>
</template>

<style scoped>
.spotlight-cutout {
	box-shadow:
		0 0 0 2px rgb(255 255 255 / 0.9),
		0 0 0 9999px rgb(0 0 0 / 0.4);
	animation: spotlight-in 300ms cubic-bezier(0.23, 1, 0.32, 1);
}

.spotlight-hint {
	animation: spotlight-in 200ms cubic-bezier(0.23, 1, 0.32, 1) 100ms backwards;
}

/* Plays once per page load, so a keyframe cannot be interrupted mid-way. */
@keyframes spotlight-in {
	from {
		opacity: 0;
	}
}

@media (prefers-reduced-motion: reduce) {
	.spotlight-cutout,
	.spotlight-hint {
		animation: none;
	}
}
</style>
