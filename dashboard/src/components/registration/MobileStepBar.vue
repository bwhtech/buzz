<template>
	<div class="sticky top-0 z-10 border-b border-outline-gray-1 bg-surface-base">
		<div class="flex h-[52px] items-center gap-1 px-1.5">
			<button
				type="button"
				class="flex size-11 flex-none items-center justify-center rounded-5 text-ink-gray-8 transition-transform duration-150 ease-out active:scale-[0.92] active:bg-surface-gray-2 disabled:invisible"
				:disabled="current === 0"
				:aria-label="__('Back')"
				@click="emit('back')"
			>
				<LucideChevronLeft class="size-5" />
			</button>
			<div class="flex min-w-0 flex-1 flex-col items-center text-center">
				<span class="max-w-full truncate text-base font-semibold text-ink-gray-9">{{ title }}</span>
				<span class="text-xs text-ink-gray-5">
					{{ __("Step {0} of {1} · {2}", [current + 1, steps.length, steps[current]?.label]) }}
				</span>
			</div>
			<div class="flex w-11 flex-none justify-center">
				<HoldPill v-if="secondsLeft" compact :seconds-left="secondsLeft" />
			</div>
		</div>
		<div class="flex gap-1 px-4 pb-2.5 pt-0.5" aria-hidden="true">
			<div
				v-for="(step, index) in steps"
				:key="step.id"
				class="h-[3px] flex-1 overflow-hidden rounded-full bg-surface-gray-3"
			>
				<div
					class="h-full origin-left rounded-full bg-surface-gray-9 transition-transform duration-[420ms] ease-[cubic-bezier(0.23,1,0.32,1)]"
					:class="index <= current ? 'scale-x-100' : 'scale-x-0'"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import LucideChevronLeft from "~icons/lucide/chevron-left"

import HoldPill from "./HoldPill.vue"
import type { RegistrationStep } from "./useRegistrationSteps"

defineProps<{
	title: string
	steps: RegistrationStep[]
	current: number
	secondsLeft: number | null
}>()
const emit = defineEmits<{ back: [] }>()
</script>
