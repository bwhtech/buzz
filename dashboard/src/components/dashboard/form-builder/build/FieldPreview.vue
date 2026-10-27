<script setup lang="ts">
import { computed } from "vue"

import { fieldType } from "../fieldTypes"
import type { DoctypeField, FormQuestion } from "../useFormBuilder"

const question = defineModel<FormQuestion>({ required: true })
const props = defineProps<{ doctypeField?: DoctypeField }>()

const fieldtype = computed(() => props.doctypeField?.fieldtype ?? question.value.fieldtype)
const options = computed(() =>
	String(question.value.options ?? props.doctypeField?.options ?? "")
		.split("\n")
		.filter(Boolean),
)
const isChoiceList = computed(() => ["Radio", "Multi Select"].includes(fieldtype.value))
const isInline = computed(() => ["Check", "Heading", "Paragraph"].includes(fieldtype.value))
const placeholder = computed(() => question.value.placeholder || "")

const BOX = "rounded-5 bg-surface-gray-2 px-3 text-p-base text-ink-gray-4"
</script>

<template>
	<hr v-if="fieldtype === 'Divider'" class="my-2 border-outline-gray-2" />

	<div v-else-if="fieldtype === 'Page Break'" class="flex items-center gap-3 py-1">
		<span class="h-px flex-1 border-t border-dashed border-outline-gray-3" />
		<input
			v-model="question.label"
			class="w-48 border-0 bg-transparent p-0 text-center text-p-sm font-medium text-ink-gray-5 outline-none focus:ring-0"
			aria-label="Step name"
		/>
		<span class="h-px flex-1 border-t border-dashed border-outline-gray-3" />
	</div>

	<div v-else class="space-y-2">
		<div class="flex items-center gap-2">
			<span
				v-if="fieldtype === 'Check'"
				class="size-4 shrink-0 rounded-[4px] border border-outline-gray-4 bg-surface-base"
				aria-hidden="true"
			/>
			<input
				v-model="question.label"
				class="min-w-[4ch] max-w-full border-0 bg-transparent p-0 text-ink-gray-8 outline-none [field-sizing:content] focus:ring-0"
				:class="
					fieldtype === 'Heading'
						? 'text-lg font-semibold text-ink-gray-9'
						: isInline
							? 'text-p-base'
							: 'text-p-sm font-medium'
				"
				:aria-label="`Label of ${fieldType(fieldtype).label} field`"
				@keydown.enter="($event.target as HTMLInputElement).blur()"
			/>
			<span
				v-if="question.mandatory || doctypeField?.locked"
				class="text-ink-red-6"
				aria-label="Required"
				>*</span
			>
		</div>

		<template v-if="!isInline">
			<div v-if="isChoiceList" class="space-y-1.5">
				<div
					v-for="option in options"
					:key="option"
					class="flex items-center gap-2 text-p-base text-ink-gray-7"
				>
					<span
						class="size-4 shrink-0 border border-outline-gray-4"
						:class="fieldtype === 'Radio' ? 'rounded-full' : 'rounded-[4px]'"
						aria-hidden="true"
					/>
					{{ option }}
				</div>
			</div>
			<div v-else-if="fieldtype === 'Rating'" class="flex gap-1 text-ink-gray-3" aria-hidden="true">
				<span v-for="star in 5" :key="star" class="lucide-star size-5" />
			</div>
			<div
				v-else-if="['Attach', 'Attach Image'].includes(fieldtype)"
				class="flex h-16 items-center justify-center gap-2 rounded-5 border border-dashed border-outline-gray-3 text-p-sm text-ink-gray-5"
			>
				<span class="lucide-upload size-4" aria-hidden="true" />
				Drop a file or browse
			</div>
			<div v-else-if="fieldtype === 'Table'" class="flex">
				<span class="rounded-5 border border-outline-gray-2 px-2.5 py-1 text-p-sm text-ink-gray-6">
					Add {{ question.label }}
				</span>
			</div>
			<div
				v-else
				:class="[
					BOX,
					['Small Text', 'Text Editor'].includes(fieldtype)
						? 'h-20 pt-2'
						: 'flex h-8 items-center justify-between',
				]"
			>
				<span class="truncate">{{ placeholder || options[0] || "" }}</span>
				<span
					v-if="['Select', 'Link', 'Date'].includes(fieldtype)"
					:class="[
						fieldtype === 'Date' ? 'lucide-calendar' : 'lucide-chevron-down',
						'size-4 shrink-0',
					]"
					aria-hidden="true"
				/>
			</div>
		</template>
		<p v-if="fieldtype === 'Paragraph'" class="text-p-base text-ink-gray-6">
			{{ question.description || "Add the text in field settings" }}
		</p>
		<p v-else-if="question.description" class="text-p-sm text-ink-gray-5">
			{{ question.description }}
		</p>
	</div>
</template>
