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
	conditional: boolean
	preview: boolean
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

const type = computed(() => fieldType(props.doctypeField?.fieldtype ?? question.value.fieldtype))
const isLayout = computed(() => type.value.group === "Layout")
const isStandard = computed(() => !!question.value.is_standard)
const isHalf = computed(() => question.value.width === "Half")

const convertTargets = computed(() =>
	Object.entries(FIELD_TYPES)
		.filter(([key, item]) =>
			isLayout.value
				? ["Heading", "Paragraph"].includes(key)
				: !["Layout", "Standard"].includes(item.group),
		)
		.map(([key, item]) => ({
			label: item.label,
			icon: item.icon,
			onClick: () => props.editor.convert(question.value, key),
		})),
)

const moreOptions = computed(() => [
	{
		label: isHalf.value ? "Full width" : "Half width",
		icon: isHalf.value ? "lucide-rectangle-horizontal" : "lucide-columns-2",
		disabled: isLayout.value,
		onClick: () => (question.value.width = isHalf.value ? "Full" : "Half"),
	},
	{
		label: question.value.enabled ? "Hide" : "Show",
		icon: question.value.enabled ? "lucide-eye-off" : "lucide-eye",
		disabled: !!props.doctypeField?.locked,
		onClick: () => (question.value.enabled = question.value.enabled ? 0 : 1),
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

function select() {
	if (!props.preview) props.editor.selected.value = question.value
}

function openSettings() {
	select()
	props.editor.settingsOpen.value = true
}
</script>

<template>
	<div
		ref="row"
		class="group relative rounded-5 px-3 py-2.5 transition-[background-color,box-shadow,opacity] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)]"
		:class="[
			preview
				? ''
				: isSelected
					? 'ring-[1.5px] ring-outline-blue-5'
					: '[@media(hover:hover)]:hover:bg-surface-gray-1',
			{ 'opacity-50': !question.enabled && !preview },
		]"
		:draggable="!preview"
		@click.stop="select"
		@dblclick="openSettings"
		@dragstart="emit('dragstart', $event)"
	>
		<div
			v-if="!preview"
			class="absolute -top-4 right-2.5 z-10 flex items-center gap-0.5 rounded-5 bg-surface-elevation-3 p-0.5 shadow-lg ring-1 ring-outline-gray-1 transition-opacity duration-150"
			:class="
				isSelected
					? 'opacity-100'
					: 'pointer-events-none opacity-0 group-focus-within:pointer-events-auto group-focus-within:opacity-100 [@media(hover:hover)]:group-hover:pointer-events-auto [@media(hover:hover)]:group-hover:opacity-100'
			"
			@click.stop
			@dblclick.stop
		>
			<span class="grid h-7 w-5 cursor-grab place-items-center text-ink-gray-4" aria-hidden="true">
				<span class="lucide-grip-vertical size-3.5" />
			</span>
			<span v-if="isStandard" class="flex h-7 items-center gap-1.5 px-2 text-p-xs text-ink-gray-7">
				<span :class="[type.icon, 'size-3.5']" aria-hidden="true" />
				<span class="whitespace-nowrap">{{ type.label }}</span>
			</span>
			<Dropdown v-else :options="convertTargets">
				<button
					type="button"
					class="flex h-7 items-center gap-1.5 rounded-5 pl-2 pr-1.5 text-p-xs text-ink-gray-7 transition-colors duration-150 [@media(hover:hover)]:hover:bg-surface-gray-2"
					:aria-label="`Turn ${type.label} into another type`"
				>
					<span :class="[type.icon, 'size-3.5']" aria-hidden="true" />
					<span class="whitespace-nowrap">{{ type.label }}</span>
					<span class="lucide-chevrons-up-down size-3 text-ink-gray-4" aria-hidden="true" />
				</button>
			</Dropdown>
			<span class="mx-0.5 h-4 w-px bg-outline-gray-2" aria-hidden="true" />
			<Tooltip
				v-if="!isLayout && !doctypeField?.locked"
				:text="question.mandatory ? 'Make optional' : 'Make mandatory'"
			>
				<Button
					:variant="question.mandatory ? 'subtle' : 'ghost'"
					size="sm"
					icon="lucide-asterisk"
					:label="question.mandatory ? 'Make optional' : 'Make mandatory'"
					@click="question.mandatory = question.mandatory ? 0 : 1"
				/>
			</Tooltip>
			<Tooltip text="Field settings · double-click">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-settings-2"
					label="Field settings"
					@click="openSettings"
				/>
			</Tooltip>
			<Dropdown :options="moreOptions" align="end">
				<Button variant="ghost" size="sm" icon="lucide-ellipsis" label="More actions" />
			</Dropdown>
		</div>

		<FieldPreview v-model="question" :doctype-field="doctypeField" :readonly="preview">
			<template v-if="!preview" #badges>
				<Badge v-if="isStandard" label="Core" theme="gray" size="sm" />
				<Badge v-if="!question.enabled" label="Hidden" theme="gray" size="sm" />
				<Badge v-if="conditional" label="Conditional" theme="blue" size="sm" />
			</template>
		</FieldPreview>
	</div>
</template>
