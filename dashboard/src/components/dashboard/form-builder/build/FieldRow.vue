<script setup lang="ts">
import { Badge, Button, Combobox, Dropdown, Tooltip } from "frappe-ui"
import { computed, ref, toRaw, watch } from "vue"

import ActionSheet from "../ActionSheet.vue"
import { FIELD_TYPES, fieldType, filterTypeGroups } from "../fieldTypes"
import type { DoctypeField, FormQuestion } from "../useFormBuilder"
import FieldPreview from "./FieldPreview.vue"
import TypeSheet from "./TypeSheet.vue"
import type { QuestionEditor } from "./useQuestionEditor"

const question = defineModel<FormQuestion>({ required: true })
const props = defineProps<{
	doctypeField?: DoctypeField
	editor: QuestionEditor
	conditional: boolean
	preview: boolean
	isFirst: boolean
	isLast: boolean
	// On a phone the row is a card: a tap opens its settings, ⋯ opens its actions.
	compact?: boolean
}>()
const emit = defineEmits<{
	dragstart: [DragEvent]
	navigate: [step: number, part: "row" | "label"]
	move: [step: number]
	remove: []
}>()

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

// Searchable, grouped like the add-field menu.
const convertTargets = computed(() => {
	const groups: Record<string, { label: string; value: string; icon: string }[]> = {}
	for (const [key, item] of Object.entries(FIELD_TYPES)) {
		const offered = isLayout.value
			? ["Heading", "Paragraph"].includes(key)
			: !["Layout", "Standard"].includes(item.group)
		if (offered)
			(groups[item.group] ??= []).push({ label: item.label, value: key, icon: item.icon })
	}
	return Object.entries(groups).map(([group, options]) => ({ group, options }))
})

const typeQuery = ref("")
const matchingTargets = computed(() => filterTypeGroups(convertTargets.value, typeQuery.value))

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

const actionsOpen = ref(false)
const typeSheetOpen = ref(false)
const sheetActions = computed(() => [
	{ label: "Field settings", icon: "lucide-settings-2", onClick: openSettings },
	{
		label: `Turn into · ${type.value.label}`,
		icon: "lucide-repeat-2",
		disabled: isStandard.value,
		onClick: () => (typeSheetOpen.value = true),
	},
	...moreOptions.value,
])

function select() {
	if (!props.preview) props.editor.selected.value = question.value
}

function openSettings() {
	select()
	props.editor.settingsOpen.value = true
}

// Notion-style keys: a focused row is a selected block; its label is the text inside it.
const sharedKeys = {
	"Mod-Enter": openSettings,
	"Mod-Shift-ArrowUp": () => emit("move", -1),
	"Mod-Shift-ArrowDown": () => emit("move", 1),
}
const rowKeys: Record<string, () => void> = {
	...sharedKeys,
	ArrowUp: () => emit("navigate", -1, "row"),
	ArrowDown: () => emit("navigate", 1, "row"),
	Enter: () => row.value?.querySelector<HTMLElement>("[data-label]")?.focus(),
	Escape: () => {
		props.editor.selected.value = null
		row.value?.blur()
	},
	"Mod-d": () => props.editor.duplicate(question.value),
	Delete: () => emit("remove"),
	Backspace: () => emit("remove"),
}
const labelKeys: Record<string, () => void> = {
	...sharedKeys,
	ArrowUp: () => emit("navigate", -1, "label"),
	ArrowDown: () => emit("navigate", 1, "label"),
	Enter: () => emit("navigate", 1, "label"),
	Escape: () => row.value?.focus(),
}

function onKeydown(event: KeyboardEvent) {
	const target = event.target as HTMLElement
	const keys = target === row.value ? rowKeys : target.hasAttribute("data-label") ? labelKeys : {}
	const modifiers = `${event.metaKey || event.ctrlKey ? "Mod-" : ""}${event.shiftKey ? "Shift-" : ""}`
	const action = keys[modifiers + event.key]
	if (!action) return
	event.preventDefault()
	action()
}
</script>

<template>
	<div
		v-if="compact"
		ref="row"
		class="flex items-start gap-1 rounded-5 py-2 pl-3.5 pr-1 transition-transform duration-150 active:scale-[0.99]"
		:class="[
			isLayout ? '' : 'bg-surface-base ring-1 ring-inset',
			isSelected && editor.settingsOpen.value ? 'ring-outline-gray-5' : 'ring-outline-gray-2',
			{ 'opacity-50': !question.enabled && !preview },
		]"
		@click.stop="!preview && openSettings()"
	>
		<div class="min-w-0 flex-1 py-2">
			<FieldPreview v-model="question" :doctype-field="doctypeField" readonly />
			<div
				v-if="!preview && (isStandard || !question.enabled || conditional || isHalf)"
				class="mt-2.5 flex flex-wrap gap-1"
			>
				<Badge v-if="isStandard" label="Core" theme="gray" size="sm" />
				<Badge v-if="!question.enabled" label="Hidden" theme="gray" size="sm" />
				<Badge v-if="conditional" label="Conditional" theme="blue" size="sm" />
				<Badge v-if="isHalf" label="Half width" theme="gray" size="sm" />
			</div>
		</div>
		<Button
			v-if="!preview"
			variant="ghost"
			size="lg"
			icon="lucide-ellipsis"
			label="More actions"
			@click.stop="actionsOpen = true"
		/>
		<ActionSheet v-model:open="actionsOpen" :title="question.label" :actions="sheetActions" />
		<TypeSheet
			v-model:open="typeSheetOpen"
			:groups="convertTargets"
			:current="question.fieldtype"
			@pick="(fieldtype) => editor.convert(question, fieldtype)"
		/>
	</div>
	<div
		v-else
		ref="row"
		class="group relative rounded-5 px-3 py-2.5 outline-none transition-[background-color,box-shadow,opacity] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)]"
		:class="[
			preview
				? ''
				: isSelected
					? 'ring-[1.5px] ring-outline-gray-9'
					: '[@media(hover:hover)]:hover:bg-surface-gray-1',
			{ 'opacity-50': !question.enabled && !preview },
		]"
		:draggable="!preview"
		:tabindex="preview ? undefined : 0"
		:aria-label="preview ? undefined : `${type.label}: ${question.label}`"
		@focusin="select"
		@keydown="onKeydown"
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
			<Combobox
				v-else
				trigger="button"
				:model-value="question.fieldtype"
				v-model:query="typeQuery"
				:options="matchingTargets"
				:filterable="false"
				@update:open="(isOpen: boolean) => isOpen || (typeQuery = '')"
				placeholder="Search field types"
				empty-text="No field type matches"
				align="start"
				@update:model-value="
					(fieldtype) => fieldtype && editor.convert(question, String(fieldtype))
				"
			>
				<template #trigger>
					<button
						type="button"
						class="flex h-7 items-center gap-1.5 rounded-5 pl-2 pr-1.5 text-p-xs text-ink-gray-7 transition-colors duration-150 [@media(hover:hover)]:hover:bg-surface-gray-2"
						:aria-label="`Turn ${type.label} into another type`"
					>
						<span :class="[type.icon, 'size-3.5']" aria-hidden="true" />
						<span class="whitespace-nowrap">{{ type.label }}</span>
						<span class="lucide-chevrons-up-down size-3 text-ink-gray-4" aria-hidden="true" />
					</button>
				</template>
			</Combobox>
			<span class="mx-0.5 h-4 w-px bg-surface-gray-3" aria-hidden="true" />
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
			<Tooltip text="Field settings · ⌘↵ or double-click">
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
