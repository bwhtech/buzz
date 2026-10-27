<script setup lang="ts">
import { Button, FormControl, Switch, TabButtons, Textarea } from "frappe-ui"
import { computed } from "vue"

import { CHOICE_TYPES, fieldType } from "../fieldTypes"
import type { DoctypeField, FormQuestion } from "../useFormBuilder"
import type { QuestionEditor } from "./useQuestionEditor"

const question = defineModel<FormQuestion>({ required: true })
const props = defineProps<{ doctypeField?: DoctypeField; editor: QuestionEditor }>()

const fieldtype = computed(() => props.doctypeField?.fieldtype ?? question.value.fieldtype)
const type = computed(() => fieldType(fieldtype.value))
const isLayout = computed(() => type.value.group === "Layout")
const takesPlaceholder = computed(() =>
	["Data", "Small Text", "Email", "Phone", "Number", "URL", "Select"].includes(fieldtype.value),
)

const WIDTHS = [
	{ label: "Full", value: "Full" },
	{ label: "Half", value: "Half" },
]

const enabled = computed({
	get: () => !!question.value.enabled,
	set: (on: boolean) => (question.value.enabled = on ? 1 : 0),
})
const mandatory = computed({
	get: () => !!question.value.mandatory,
	set: (on: boolean) => (question.value.mandatory = on ? 1 : 0),
})
</script>

<template>
	<div class="flex h-full flex-col">
		<header class="flex items-center gap-2 border-b border-outline-gray-1 px-4 py-3">
			<span :class="[type.icon, 'size-4 text-ink-gray-6']" aria-hidden="true" />
			<h2 class="flex-1 text-p-base font-medium text-ink-gray-9">{{ type.label }}</h2>
			<Button
				variant="ghost"
				icon="lucide-x"
				label="Close field settings"
				@click="editor.selected.value = null"
			/>
		</header>

		<div class="flex-1 space-y-5 overflow-y-auto p-4">
			<p
				v-if="question.is_standard"
				class="rounded-5 bg-surface-gray-2 px-3 py-2 text-p-sm text-ink-gray-6"
			>
				{{
					doctypeField?.locked
						? "Added by Buzz and always asked. You can rename and move it."
						: "Added by Buzz. You can rename, move or hide it, not delete it."
				}}
			</p>

			<FormControl
				v-if="fieldtype !== 'Divider'"
				v-model="question.label"
				:label="
					fieldtype === 'Page Break' ? 'Step name' : fieldtype === 'Heading' ? 'Heading' : 'Label'
				"
			/>
			<FormControl
				v-if="takesPlaceholder && !question.is_standard"
				v-model="question.placeholder"
				label="Placeholder"
			/>
			<Textarea
				v-if="!['Divider', 'Page Break'].includes(fieldtype)"
				:model-value="question.description ?? ''"
				@update:model-value="question.description = $event"
				:label="fieldtype === 'Paragraph' ? 'Text' : 'Help text'"
				:rows="fieldtype === 'Paragraph' ? 4 : 2"
			/>
			<Textarea
				v-if="CHOICE_TYPES.includes(fieldtype)"
				:model-value="question.options ?? ''"
				@update:model-value="question.options = $event"
				label="Options"
				description="One option per line"
				:rows="5"
			/>

			<div v-if="!isLayout" class="space-y-1.5">
				<span class="text-p-xs text-ink-gray-5">Width</span>
				<TabButtons v-model="question.width" :options="WIDTHS" fluid />
			</div>

			<div class="space-y-3">
				<Switch
					v-if="!isLayout && !doctypeField?.locked && !question.is_standard"
					v-model="mandatory"
					label="Mandatory"
				/>
				<Switch v-if="!doctypeField?.locked" v-model="enabled" label="Show on the form" />
			</div>
		</div>

		<footer v-if="!question.is_standard" class="flex gap-2 border-t border-outline-gray-1 p-3">
			<Button
				class="flex-1"
				icon-left="lucide-copy"
				label="Duplicate"
				@click="editor.duplicate(question)"
			/>
			<Button
				class="flex-1"
				theme="red"
				icon-left="lucide-trash-2"
				label="Delete"
				@click="editor.remove(question)"
			/>
		</footer>
	</div>
</template>
