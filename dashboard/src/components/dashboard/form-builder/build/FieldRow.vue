<script setup lang="ts">
import { Badge } from "frappe-ui"
import { computed } from "vue"

import { fieldType } from "../fieldTypes"
import type { DoctypeField, FormQuestion } from "../useFormBuilder"

const question = defineModel<FormQuestion>({ required: true })
// Set for a standard row: the doctype field it stands for.
const props = defineProps<{ doctypeField?: DoctypeField }>()

const type = computed(() => fieldType(props.doctypeField?.fieldtype ?? question.value.fieldtype))

const LABEL_CLASSES: Record<string, string> = {
	Heading: "text-lg font-semibold",
	"Page Break": "text-p-sm font-medium uppercase tracking-wide text-ink-gray-5",
}
</script>

<template>
	<div
		class="group flex items-center gap-3 rounded-4 px-3 py-2.5 transition-colors duration-150 focus-within:bg-surface-gray-1 [@media(hover:hover)]:hover:bg-surface-gray-1"
		:class="{ 'opacity-50': !question.enabled }"
	>
		<span :class="[type.icon, 'size-4 shrink-0 text-ink-gray-5']" aria-hidden="true" />
		<hr v-if="question.fieldtype === 'Divider'" class="flex-1 border-outline-gray-2" />
		<input
			v-else
			v-model="question.label"
			class="min-w-0 flex-1 border-0 bg-transparent p-0 text-ink-gray-9 outline-none focus:ring-0"
			:class="LABEL_CLASSES[question.fieldtype] ?? 'text-p-base font-medium'"
			:aria-label="`Label of ${type.label} field`"
			@keydown.enter="($event.target as HTMLInputElement).blur()"
		/>
		<Badge v-if="question.is_standard" label="Core" theme="gray" size="sm" />
		<Badge
			v-if="question.mandatory || doctypeField?.locked"
			label="Required"
			theme="gray"
			size="sm"
		/>
		<Badge v-if="question.width === 'Half'" label="Half width" theme="gray" size="sm" />
		<span class="text-p-sm text-ink-gray-4">{{ type.label }}</span>
	</div>
</template>
