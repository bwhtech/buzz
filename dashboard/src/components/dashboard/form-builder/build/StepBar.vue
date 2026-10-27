<script setup lang="ts">
import { BottomSheet, Button, Tooltip } from "frappe-ui"
import { computed, ref } from "vue"

import type { FormQuestion } from "../useFormBuilder"
import type { Steps } from "./useSteps"

const props = defineProps<{
	steps: Steps
	questions: FormQuestion[]
	compact?: boolean
	// The phone-width canvas names only the step on screen.
	tight?: boolean
	editable?: boolean
}>()

const sheetOpen = ref(false)
const current = computed(() => props.steps.stepIndex.value)
const count = computed(() => props.steps.steps.value.length)

function goTo(index: number) {
	props.steps.go(index)
	sheetOpen.value = false
}

const fieldCount = (index: number) => {
	const { start, end } = props.steps.steps.value[index]
	const fields = props.questions.slice(start, end).length
	return `${fields} ${fields === 1 ? "field" : "fields"}`
}
</script>

<template>
	<template v-if="compact">
		<div
			class="mb-3 flex flex-col gap-2.5 rounded-5 bg-surface-gray-1 p-1.5 pb-3 ring-1 ring-inset ring-outline-gray-1"
			@click.stop
		>
			<div class="grid grid-cols-[40px_minmax(0,1fr)_40px] items-center gap-1">
				<Button
					variant="ghost"
					size="lg"
					icon="lucide-chevron-left"
					label="Previous step"
					:disabled="current === 0"
					@click="steps.go(current - 1)"
				/>
				<button
					type="button"
					class="flex h-10 min-w-0 flex-col items-center justify-center gap-px rounded-5"
					:disabled="!editable"
					@click="sheetOpen = true"
				>
					<span class="text-[11px] tracking-[0.02em] text-ink-gray-5"
						>Step {{ current + 1 }} of {{ count }}</span
					>
					<span class="flex max-w-full items-center gap-1 text-p-base font-medium text-ink-gray-9">
						<span class="truncate">{{ steps.step.value.name || `Step ${current + 1}` }}</span>
						<span
							v-if="editable"
							class="lucide-chevrons-up-down size-3 shrink-0 text-ink-gray-4"
							aria-hidden="true"
						/>
					</span>
				</button>
				<Button
					variant="ghost"
					size="lg"
					icon="lucide-chevron-right"
					label="Next step"
					:disabled="current >= count - 1"
					@click="steps.go(current + 1)"
				/>
			</div>
			<div class="flex gap-1 px-2" aria-hidden="true">
				<span
					v-for="index in count"
					:key="index"
					class="h-1 flex-1 rounded-full transition-colors duration-200"
					:class="index - 1 <= current ? 'bg-surface-gray-10' : 'bg-surface-gray-3'"
				/>
			</div>
		</div>

		<BottomSheet v-model:open="sheetOpen" title="Steps">
			<div class="flex flex-col gap-1 px-4 pb-6">
				<div
					v-for="(step, index) in steps.steps.value"
					:key="index"
					class="flex items-center gap-3 py-1.5"
				>
					<button
						type="button"
						class="grid size-8 shrink-0 place-items-center rounded-full text-p-sm font-semibold"
						:class="
							index === current
								? 'bg-surface-gray-10 text-ink-base'
								: 'bg-surface-gray-2 text-ink-gray-7'
						"
						:aria-label="`Go to step ${index + 1}`"
						@click="goTo(index)"
					>
						{{ index + 1 }}
					</button>
					<div class="flex min-w-0 flex-1 flex-col">
						<input
							:value="step.name"
							placeholder="Step name"
							:aria-label="`Name of step ${index + 1}`"
							class="border-0 bg-transparent p-0 text-[15px] font-medium text-ink-gray-9 outline-none placeholder:font-normal placeholder:text-ink-gray-4 focus:ring-0"
							@change="steps.rename(($event.target as HTMLInputElement).value, index)"
						/>
						<span class="text-p-xs text-ink-gray-5">{{ fieldCount(index) }}</span>
					</div>
					<Button
						v-if="index > 0"
						variant="ghost"
						size="lg"
						icon="lucide-trash-2"
						:label="`Remove step ${index + 1}`"
						@click="steps.remove(index)"
					/>
				</div>
				<Button
					class="mt-2 w-full"
					size="lg"
					icon-left="lucide-plus"
					label="Add step"
					@click="steps.add"
				/>
				<p class="text-center text-p-xs text-ink-gray-5">
					Removing a step moves its fields into the step before it
				</p>
			</div>
		</BottomSheet>
	</template>

	<div
		v-else-if="steps.steps.value.length > 1"
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
						index === steps.stepIndex.value
							? 'bg-surface-gray-10 text-ink-base'
							: 'bg-surface-base text-ink-gray-5 ring-1 ring-inset ring-outline-gray-3'
					"
				>
					{{ index + 1 }}
				</span>
				<span
					v-if="index === steps.stepIndex.value || (!props.tight && steps.steps.value.length <= 4)"
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
				class="h-px min-w-2 flex-1 bg-surface-gray-3"
				aria-hidden="true"
			/>
		</template>
	</div>

	<div
		v-if="props.editable && !compact"
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
