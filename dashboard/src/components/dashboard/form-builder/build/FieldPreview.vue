<script setup lang="ts">
import { computed } from "vue"

import { fieldType } from "../fieldTypes"
import type { DoctypeField, FormQuestion } from "../useFormBuilder"
import ParagraphEditor from "./ParagraphEditor.vue"

const question = defineModel<FormQuestion>({ required: true })
const props = defineProps<{ doctypeField?: DoctypeField; readonly?: boolean }>()

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

	<div v-else>
		<div v-if="fieldtype === 'Paragraph'" class="mb-1 flex gap-1.5 empty:hidden">
			<slot name="badges" />
		</div>
		<div
			v-else
			class="flex min-h-[22px] flex-wrap items-center gap-1.5"
			:class="{ 'mb-2': !isInline }"
		>
			<span
				v-if="fieldtype === 'Check'"
				class="size-4 shrink-0 rounded-1 border border-outline-gray-4 bg-surface-base"
				aria-hidden="true"
			/>
			<input
				v-model="question.label"
				:readonly="readonly"
				class="border-0 bg-transparent p-0 text-ink-gray-9 outline-none focus:ring-0"
				:class="[
					readonly ? 'max-w-full [field-sizing:content]' : 'min-w-[120px] flex-1',
					fieldtype === 'Heading' ? 'text-lg font-semibold' : 'text-[14px] font-medium',
				]"
				:aria-label="`Label of ${fieldType(fieldtype).label} field`"
				data-label
			/>
			<span
				v-if="question.mandatory || doctypeField?.locked"
				class="text-[14px] leading-none text-ink-red-4"
				aria-label="Required"
				>*</span
			>
			<slot name="badges" />
		</div>

		<template v-if="!isInline">
			<div v-if="isChoiceList" class="space-y-2">
				<div
					v-for="option in options"
					:key="option"
					class="flex items-center gap-2.5 text-p-base text-ink-gray-7"
				>
					<span
						class="size-4 shrink-0 border border-outline-gray-4"
						:class="fieldtype === 'Radio' ? 'rounded-full' : 'rounded-1'"
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
				class="flex h-20 items-center justify-center gap-2 rounded-5 border border-dashed border-outline-gray-3 text-p-sm text-ink-gray-5"
			>
				<span class="lucide-upload size-4" aria-hidden="true" />
				Drop a file or browse
			</div>
			<div v-else-if="fieldtype === 'Table'" class="flex">
				<span
					class="rounded-5 border border-outline-gray-2 px-3 py-1.5 text-p-base text-ink-gray-8"
				>
					Add {{ question.label }}
				</span>
			</div>
			<div
				v-else
				:class="[
					BOX,
					['Small Text', 'Text Editor'].includes(fieldtype)
						? 'h-[120px] pt-2.5'
						: 'flex h-[38px] items-center justify-between',
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
		<template v-if="fieldtype === 'Paragraph'">
			<div
				v-if="readonly"
				class="prose prose-sm max-w-none text-ink-gray-7"
				v-html="question.description"
			/>
			<ParagraphEditor v-else v-model="question.description" />
		</template>
		<p v-else-if="question.description" class="mt-1.5 text-p-sm text-ink-gray-5">
			{{ question.description }}
		</p>
	</div>
</template>
