<script setup lang="ts">
import { Badge, Button, Dropdown, Tooltip } from "frappe-ui"
import { computed, ref, toRaw, watch } from "vue"

import { FIELD_TYPES, fieldType } from "../fieldTypes"
import type { DoctypeField, FormQuestion } from "../useFormBuilder"
import FieldPreview from "./FieldPreview.vue"
import type { QuestionEditor } from "./useQuestionEditor"

const question = defineModel<FormQuestion>({ required: true })
const props = defineProps<{
	doctypeField?: DoctypeField
	editor: QuestionEditor
	isFirst: boolean
	isLast: boolean
}>()
const emit = defineEmits<{ dragstart: [DragEvent] }>()

const isSelected = computed(
	() =>
		!!props.editor.selected.value && toRaw(props.editor.selected.value) === toRaw(question.value),
)
const row = ref<HTMLElement | null>(null)
watch(isSelected, (selected) => selected && row.value?.scrollIntoView({ block: "nearest" }))

const isLayout = computed(() => fieldType(question.value.fieldtype).group === "Layout")
const isStandard = computed(() => !!question.value.is_standard)
const canHide = computed(() => !props.doctypeField?.locked)

const convertTargets = computed(() =>
	Object.entries(FIELD_TYPES)
		.filter(([key, type]) =>
			isLayout.value
				? ["Heading", "Paragraph"].includes(key)
				: !["Layout", "Standard"].includes(type.group),
		)
		.map(([key, type]) => ({
			label: type.label,
			icon: type.icon,
			selected: key === question.value.fieldtype,
			onClick: () => props.editor.convert(question.value, key),
		})),
)

const moreOptions = computed(() => [
	{
		label: "Field settings",
		icon: "lucide-settings-2",
		onClick: () => {
			props.editor.selected.value = question.value
			props.editor.settingsOpen.value = true
		},
	},
	{
		label: "Turn into",
		icon: "lucide-repeat-2",
		disabled: isStandard.value,
		submenu: convertTargets.value,
	},
	{
		label: "Duplicate",
		icon: "lucide-copy",
		disabled: isStandard.value,
		onClick: () => props.editor.duplicate(question.value),
	},
	{
		label: "Move up",
		icon: "lucide-arrow-up",
		disabled: props.isFirst,
		onClick: () => props.editor.move(question.value, props.editor.indexOf(question.value) - 1),
	},
	{
		label: "Move down",
		icon: "lucide-arrow-down",
		disabled: props.isLast,
		onClick: () => props.editor.move(question.value, props.editor.indexOf(question.value) + 2),
	},
	{
		label: "Delete",
		icon: "lucide-trash-2",
		theme: "red" as const,
		disabled: isStandard.value,
		onClick: () => props.editor.remove(question.value),
	},
])

function toggleHidden() {
	question.value.enabled = question.value.enabled ? 0 : 1
}

function toggleRequired() {
	question.value.mandatory = question.value.mandatory ? 0 : 1
}
</script>

<template>
	<div
		ref="row"
		class="group relative rounded-6 px-3 py-3 transition-[background-color,box-shadow] duration-150"
		:class="[
			isSelected
				? 'bg-surface-base ring-[1.5px] ring-outline-gray-5'
				: '[@media(hover:hover)]:hover:bg-surface-gray-1',
			{ 'opacity-50': !question.enabled },
		]"
		draggable="true"
		@click.stop="editor.selected.value = question"
		@dragstart="emit('dragstart', $event)"
	>
		<div class="mb-1 flex h-5 items-center gap-1.5">
			<span
				:class="[
					fieldType(doctypeField?.fieldtype ?? question.fieldtype).icon,
					'size-3.5 text-ink-gray-4',
				]"
				aria-hidden="true"
			/>
			<span class="text-p-xs text-ink-gray-4">{{
				fieldType(doctypeField?.fieldtype ?? question.fieldtype).label
			}}</span>
			<Badge v-if="isStandard" label="Core" theme="gray" size="sm" />
			<Badge v-if="!question.enabled" label="Hidden" theme="gray" size="sm" />
			<Badge v-if="question.width === 'Half'" label="Half" theme="gray" size="sm" />
		</div>

		<FieldPreview v-model="question" :doctype-field="doctypeField" />

		<div
			class="absolute right-2 top-2 flex items-center gap-0.5 rounded-5 bg-surface-base p-0.5 shadow-sm ring-1 ring-outline-gray-1 transition-opacity duration-150"
			:class="
				isSelected
					? 'opacity-100'
					: 'opacity-0 group-hover:opacity-100 group-focus-within:opacity-100'
			"
			@click.stop
		>
			<Tooltip
				v-if="!isLayout && !doctypeField?.locked"
				:text="question.mandatory ? 'Make optional' : 'Make mandatory'"
			>
				<Button
					:variant="question.mandatory ? 'subtle' : 'ghost'"
					size="sm"
					icon="lucide-asterisk"
					:label="question.mandatory ? 'Make optional' : 'Make mandatory'"
					@click="toggleRequired"
				/>
			</Tooltip>
			<Tooltip v-if="canHide" :text="question.enabled ? 'Hide' : 'Show'">
				<Button
					variant="ghost"
					size="sm"
					:icon="question.enabled ? 'lucide-eye' : 'lucide-eye-off'"
					:label="question.enabled ? 'Hide' : 'Show'"
					@click="toggleHidden"
				/>
			</Tooltip>
			<Dropdown :options="moreOptions" align="end">
				<Button variant="ghost" size="sm" icon="lucide-ellipsis" label="More actions" />
			</Dropdown>
		</div>
	</div>
</template>
