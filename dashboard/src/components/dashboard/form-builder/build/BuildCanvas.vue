<script setup lang="ts">
import { breakpointsTailwind, useBreakpoints, useEventListener } from "@vueuse/core"
import { BottomSheet, Button } from "frappe-ui"
import { computed, ref, toRaw } from "vue"

import type { MenuItem } from "../fieldTypes"
import type { BuzzFormDoc, DoctypeField, FormQuestion } from "../useFormBuilder"
import FieldComposer from "./FieldComposer.vue"
import FieldInspector from "./FieldInspector.vue"
import FieldPalette from "./FieldPalette.vue"
import FieldRow from "./FieldRow.vue"
import { type QuestionEditor, newQuestion, questionKey } from "./useQuestionEditor"

const form = defineModel<BuzzFormDoc>({ required: true })
const props = defineProps<{
	doctypeFields: Record<string, DoctypeField>
	editor: QuestionEditor
	// What the booking page always asks before these questions.
	fixedFields?: string[]
}>()
defineEmits<{ addRule: [FormQuestion] }>()

const editor = props.editor
const composer = ref<InstanceType<typeof FieldComposer> | null>(null)

const selectedIndex = computed(() =>
	editor.selected.value ? editor.indexOf(editor.selected.value) : -1,
)

// Below lg the side panel is gone: settings and the palette open as bottom sheets.
const isNarrow = useBreakpoints(breakpointsTailwind).smaller("lg")
const paletteOpen = ref(false)
const inspectorOpen = computed({
	get: () => isNarrow.value && selectedIndex.value >= 0 && editor.settingsOpen.value,
	set: (open) => (editor.settingsOpen.value = open),
})

// The side panel and the phone sheet show the same settings.
const inspectorProps = computed(() => {
	const question = form.value.questions[selectedIndex.value]
	return {
		doctypeField: doctypeFieldOf(question),
		editor,
		ruleCount: rulesActingOn(question),
		rules: form.value.logic_rules,
		ticketTypes:
			form.value.form_doctype === "Event Booking Attendee"
				? props.doctypeFields.ticket_type?.link_options
				: null,
	}
})

function addFromSheet(item: MenuItem) {
	paletteOpen.value = false
	addItem(item)
}

const doctypeFieldOf = (question: FormQuestion) =>
	question.is_standard ? props.doctypeFields[question.fieldname] : undefined

// What is being dragged: a row being moved, or a palette item being added.
const dragged = ref<FormQuestion | MenuItem | null>(null)
const dropIndex = ref<number | null>(null)

function onRowDragOver(index: number, event: DragEvent) {
	if (!dragged.value) return
	event.preventDefault()
	const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
	dropIndex.value = event.clientY < box.top + box.height / 2 ? index : index + 1
}

function onDrop() {
	const item = dragged.value
	const at = dropIndex.value ?? form.value.questions.length
	if (item && "fields" in item) addItem(item as MenuItem, at)
	else if (item) editor.move(item as FormQuestion, at)
	endDrag()
}

function endDrag() {
	dragged.value = null
	dropIndex.value = null
}

function addItem(item: MenuItem, at?: number) {
	const added = item.fields.map(newQuestion)
	if (at === undefined) editor.insertAfterSelection(added)
	else editor.insert(at, added)
}

const rulesActingOn = (question: FormQuestion) =>
	form.value.logic_rules.filter((rule) =>
		rule.actions.some(([, target]) => target === question.fieldname),
	).length

function isTyping(event: KeyboardEvent) {
	const target = event.target as HTMLElement
	return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
}

// A drag cancelled anywhere still ends here, so no stale drop line is left behind.
useEventListener(window, "dragend", endDrag)

useEventListener(window, "keydown", (event: KeyboardEvent) => {
	const selected = editor.selected.value
	if (event.key === "Escape") editor.selected.value = null
	if (isTyping(event)) return
	if (event.key === "/") {
		event.preventDefault()
		composer.value?.focus()
	} else if (selected && (event.metaKey || event.ctrlKey) && event.key === "d") {
		event.preventDefault()
		editor.duplicate(selected)
	} else if (selected && ["Delete", "Backspace"].includes(event.key)) {
		editor.remove(selected)
	}
})
</script>

<template>
	<div class="flex h-full min-h-0">
		<div class="min-w-0 flex-1 overflow-y-auto" @click="editor.selected.value = null">
			<div class="mx-auto w-full max-w-[760px] px-4 pb-24 pt-8 sm:px-7">
				<div class="rounded-8 bg-surface-base p-5 shadow-sm ring-1 ring-outline-gray-1 sm:p-8">
					<input
						v-model="form.title"
						class="w-full border-0 bg-transparent p-0 text-2xl font-semibold text-ink-gray-9 outline-none focus:ring-0"
						aria-label="Form name"
						@click.stop
					/>
					<textarea
						v-model="form.description"
						rows="1"
						class="mb-6 mt-1 w-full resize-none border-0 bg-transparent p-0 text-p-base text-ink-gray-6 outline-none [field-sizing:content] placeholder:text-ink-gray-4 focus:ring-0"
						placeholder="Add a description"
						aria-label="Form description"
						@click.stop
					/>

					<p
						v-if="fixedFields?.length"
						class="mb-3 flex flex-wrap items-center gap-1.5 text-p-sm text-ink-gray-5"
					>
						<span class="lucide-lock size-3.5" aria-hidden="true" />
						Always asked:
						<span
							v-for="label in fixedFields"
							:key="label"
							class="rounded-5 bg-surface-gray-2 px-1.5 py-0.5 text-ink-gray-7"
						>
							{{ label }}
						</span>
					</p>
					<div
						class="-mx-3 grid grid-cols-1 gap-x-2 gap-y-1 md:grid-cols-2"
						@dragover.prevent
						@drop.prevent="onDrop"
					>
						<div
							v-for="(question, index) in form.questions"
							:key="questionKey(question)"
							class="relative"
							:class="{
								'md:col-span-2': question.width !== 'Half',
								'opacity-40': dragged && toRaw(dragged) === toRaw(question),
							}"
							@dragover="onRowDragOver(index, $event)"
						>
							<span
								v-if="dropIndex === index"
								class="absolute inset-x-3 -top-1 h-0.5 rounded-full bg-surface-gray-7"
								aria-hidden="true"
							/>
							<FieldRow
								v-model="form.questions[index]"
								:doctype-field="doctypeFieldOf(question)"
								:editor="editor"
								:is-first="index === 0"
								:is-last="index === form.questions.length - 1"
								@dragstart="dragged = question"
							/>
						</div>
						<div
							class="relative md:col-span-2"
							@dragover.prevent="dropIndex = form.questions.length"
							@click.stop
						>
							<span
								v-if="dropIndex === form.questions.length"
								class="absolute inset-x-3 -top-1 h-0.5 rounded-full bg-surface-gray-7"
								aria-hidden="true"
							/>
							<FieldComposer ref="composer" :form-doctype="form.form_doctype" @pick="addItem" />
						</div>
					</div>
				</div>
			</div>
		</div>

		<aside
			class="hidden w-[300px] shrink-0 border-l border-outline-gray-1 bg-surface-base lg:block"
		>
			<FieldInspector
				v-if="selectedIndex >= 0"
				:key="questionKey(form.questions[selectedIndex])"
				v-model="form.questions[selectedIndex]"
				v-bind="inspectorProps"
				@add-rule="$emit('addRule', form.questions[selectedIndex])"
			/>
			<FieldPalette
				v-else
				:form-doctype="form.form_doctype"
				@pick="addItem"
				@dragstart="(item) => (dragged = item)"
			/>
		</aside>
		<BottomSheet v-if="isNarrow" v-model:open="inspectorOpen" title="Field settings">
			<FieldInspector
				v-if="selectedIndex >= 0"
				:key="questionKey(form.questions[selectedIndex])"
				v-model="form.questions[selectedIndex]"
				v-bind="inspectorProps"
				@add-rule="$emit('addRule', form.questions[selectedIndex])"
			/>
		</BottomSheet>
		<BottomSheet v-if="isNarrow" v-model:open="paletteOpen" title="Add a field">
			<FieldPalette :form-doctype="form.form_doctype" @pick="addFromSheet" />
		</BottomSheet>
		<Button
			v-if="isNarrow"
			variant="solid"
			size="lg"
			icon="lucide-plus"
			label="Add a field"
			class="fixed bottom-[max(1rem,env(safe-area-inset-bottom))] right-4 z-10 !size-12 !rounded-full shadow-lg active:scale-95 transition-transform duration-150"
			@click="paletteOpen = true"
		/>
	</div>
</template>
