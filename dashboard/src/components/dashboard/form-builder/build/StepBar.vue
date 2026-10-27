<script setup lang="ts">
import { Button, Tooltip } from "frappe-ui"

import type { Steps } from "./useSteps"

const props = defineProps<{ steps: Steps; compact?: boolean; editable?: boolean }>()
</script>

<template>
	<div
		v-if="steps.steps.value.length > 1"
		class="mb-7 flex min-w-0 items-center gap-2.5 overflow-hidden"
		@click.stop
	>
		<template v-for="(step, index) in steps.steps.value" :key="index">
			<button
				type="button"
				class="flex shrink-0 items-center gap-2"
				:aria-current="index === steps.stepIndex.value ? 'step' : undefined"
				@click="steps.go(index)"
			>
				<span
					class="grid size-[22px] place-items-center rounded-full text-p-xs font-semibold transition-colors duration-200"
					:class="
						index <= steps.stepIndex.value
							? 'bg-surface-gray-7 text-ink-white'
							: 'bg-surface-base text-ink-gray-5 ring-1 ring-inset ring-outline-gray-3'
					"
				>
					{{ index + 1 }}
				</span>
				<span
					v-if="
						index === steps.stepIndex.value || (!props.compact && steps.steps.value.length <= 4)
					"
					class="whitespace-nowrap text-p-sm"
					:class="
						index === steps.stepIndex.value ? 'font-medium text-ink-gray-9' : 'text-ink-gray-5'
					"
				>
					{{ step.name || `Step ${index + 1}` }}
				</span>
			</button>
			<span
				v-if="index < steps.steps.value.length - 1"
				class="h-px min-w-2 flex-1 bg-outline-gray-2"
				aria-hidden="true"
			/>
		</template>
	</div>

	<div
		v-if="props.editable"
		class="mb-3 flex items-center gap-2 border-b border-dashed border-outline-gray-2 pb-2.5"
		@click.stop
	>
		<span class="whitespace-nowrap text-p-xs text-ink-gray-5">
			Step {{ steps.stepIndex.value + 1 }} of {{ steps.steps.value.length }}
		</span>
		<input
			:value="steps.step.value.name"
			placeholder="Step name"
			aria-label="Step name"
			class="min-w-0 flex-1 border-0 bg-transparent p-0 text-[15px] font-semibold text-ink-gray-9 outline-none placeholder:font-normal placeholder:text-ink-gray-4 focus:ring-0"
			@change="steps.rename(($event.target as HTMLInputElement).value)"
		/>
		<Tooltip v-if="steps.stepIndex.value > 0" text="Remove step · fields join the previous one">
			<Button
				variant="ghost"
				size="sm"
				icon="lucide-trash-2"
				label="Remove step"
				@click="steps.remove"
			/>
		</Tooltip>
		<Button
			variant="subtle"
			size="sm"
			icon-left="lucide-plus"
			label="Add step"
			@click="steps.add"
		/>
	</div>
</template>
