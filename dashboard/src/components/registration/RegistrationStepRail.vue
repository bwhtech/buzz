<template>
	<nav :aria-label="__('Registration steps')" class="flex flex-col">
		<button
			v-for="(step, index) in steps"
			:key="step.id"
			type="button"
			class="flex gap-3 text-left disabled:cursor-default"
			:disabled="index >= current"
			:aria-current="index === current ? 'step' : undefined"
			@click="emit('go', index)"
		>
			<div class="flex flex-col items-center">
				<span
					class="flex size-[22px] flex-none items-center justify-center rounded-full text-xs transition-colors duration-200"
					:class="markerClass(index)"
				>
					<LucideCheck v-if="index < current" class="size-3" />
					<template v-else>{{ index + 1 }}</template>
				</span>
				<span
					v-if="index < steps.length - 1"
					class="my-1 min-h-[26px] flex-1 border-l border-outline-gray-2"
				/>
			</div>
			<div class="flex flex-col gap-0.5 pb-[18px] pt-0.5">
				<span class="text-base" :class="labelClass(index)">{{ step.label }}</span>
				<span class="text-p-sm text-ink-gray-5">{{ step.sub }}</span>
			</div>
		</button>
	</nav>
</template>

<script setup lang="ts">
import LucideCheck from "~icons/lucide/check"

import type { RegistrationStep } from "./useRegistrationSteps"

const props = defineProps<{ steps: RegistrationStep[]; current: number }>()
const emit = defineEmits<{ go: [index: number] }>()

function markerClass(index: number) {
	if (index < props.current) return "bg-surface-gray-9 text-ink-base"
	if (index === props.current)
		return "border-[1.5px] border-outline-gray-9 font-semibold text-ink-gray-9"
	return "border border-outline-gray-2 text-ink-gray-5"
}

function labelClass(index: number) {
	if (index === props.current) return "font-semibold text-ink-gray-9"
	return index < props.current ? "text-ink-gray-7" : "text-ink-gray-5"
}
</script>
