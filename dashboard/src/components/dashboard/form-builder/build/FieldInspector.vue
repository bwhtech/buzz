<script setup lang="ts">
import { Button, FormControl, Switch, TabButtons, Textarea } from "frappe-ui"
import { computed } from "vue"

import type { LogicRule } from "@/utils/formLogic"

import { CHOICE_TYPES, fieldType } from "../fieldTypes"
import type { DoctypeField, FormQuestion } from "../useFormBuilder"
import OptionsEditor from "./OptionsEditor.vue"
import ParagraphEditor from "./ParagraphEditor.vue"
import TicketTypePicker from "./TicketTypePicker.vue"
import type { QuestionEditor } from "./useQuestionEditor"

const question = defineModel<FormQuestion>({ required: true })
const props = defineProps<{
	doctypeField?: DoctypeField
	editor: QuestionEditor
	ruleCount: number
	rules: LogicRule[]
	// Set on the attendee form, where a question can be asked for some tickets only.
	ticketTypes?: { value: string; label: string }[] | null
}>()
defineEmits<{ addRule: []; close: [] }>()

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
		<header class="flex items-center gap-2.5 px-4 pb-1 pt-4">
			<span class="grid size-7 place-items-center rounded-5 bg-surface-gray-2 text-ink-gray-7">
				<span :class="[type.icon, 'size-4']" aria-hidden="true" />
			</span>
			<div class="flex min-w-0 flex-1 flex-col gap-0.5">
				<h2 class="text-p-base font-semibold text-ink-gray-9">{{ type.label }}</h2>
				<span v-if="question.fieldname" class="truncate font-mono text-p-xs text-ink-gray-5">
					{{ question.fieldname }}
				</span>
			</div>
			<template v-if="!question.is_standard">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-layers-2"
					label="Duplicate"
					@click="editor.duplicate(question)"
				/>
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-trash-2"
					label="Delete"
					@click="editor.remove(question)"
				/>
			</template>
			<Button
				variant="ghost"
				size="sm"
				icon="lucide-x"
				label="Close field settings"
				@click="$emit('close')"
			/>
		</header>

		<div class="flex-1 space-y-4 overflow-y-auto p-4">
			<p
				v-if="question.is_standard"
				class="flex gap-2.5 rounded-5 bg-surface-gray-1 px-3 py-2.5 text-p-xs leading-normal text-ink-gray-6 ring-1 ring-inset ring-outline-gray-1"
			>
				<span class="lucide-lock mt-0.5 size-3.5 shrink-0 text-ink-gray-5" aria-hidden="true" />
				{{
					doctypeField?.locked
						? "Added by Buzz and always asked. You can rename and move it."
						: "Added by Buzz. You can rename, move or hide it, not delete it."
				}}
			</p>

			<FormControl
				v-if="!['Divider', 'Paragraph'].includes(fieldtype)"
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
			<div v-if="fieldtype === 'Paragraph'" class="flex flex-col gap-1.5">
				<span class="text-xs text-ink-gray-5">Text</span>
				<ParagraphEditor
					v-model="question.description"
					content-class="min-h-24 rounded-5 bg-surface-gray-2 px-3 py-2"
				/>
			</div>
			<Textarea
				v-else-if="!['Divider', 'Page Break'].includes(fieldtype)"
				:model-value="question.description ?? ''"
				@update:model-value="question.description = $event"
				label="Description"
				:rows="2"
			/>
			<OptionsEditor v-if="CHOICE_TYPES.includes(fieldtype)" v-model="question.options" />

			<TicketTypePicker
				v-if="ticketTypes?.length && !isLayout && !question.is_standard"
				:rules="rules"
				:fieldname="editor.ensureFieldname(question)"
				:ticket-types="ticketTypes"
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

			<section v-if="!question.is_standard" class="space-y-2 border-t border-outline-gray-1 pt-4">
				<h3 class="text-p-sm font-medium text-ink-gray-8">Logic</h3>
				<p class="text-p-sm text-ink-gray-5">
					{{
						ruleCount
							? `${ruleCount} ${ruleCount === 1 ? "rule changes" : "rules change"} this field.`
							: "Always asked, unless a rule says otherwise."
					}}
				</p>
				<Button icon-left="lucide-workflow" label="Add a rule" @click="$emit('addRule')" />
			</section>
		</div>
	</div>
</template>
