<script setup lang="ts">
import { breakpointsTailwind, useBreakpoints, useEventListener } from "@vueuse/core"
import { BottomSheet, Button } from "frappe-ui"
import { computed, nextTick, ref, toRaw, watch } from "vue"

import { useIsMobile } from "@/composables/useIsMobile"

import { ADD_STEP, type MenuItem, takesSteps } from "../fieldTypes"
import type { BuzzFormDoc, DoctypeField, FormQuestion } from "../useFormBuilder"
import AddFieldSheet from "./AddFieldSheet.vue"
import FieldComposer from "./FieldComposer.vue"
import FieldInspector from "./FieldInspector.vue"
import FieldRow from "./FieldRow.vue"
import FormHeader from "./FormHeader.vue"
import StepBar from "./StepBar.vue"
import { type QuestionEditor, newQuestion, questionKey } from "./useQuestionEditor"
import { useSteps } from "./useSteps"

const form = defineModel<BuzzFormDoc>({ required: true })
const props = defineProps<{
	doctypeFields: Record<string, DoctypeField>
	editor: QuestionEditor
	device: "desktop" | "mobile"
	preview: boolean
	// What the booking page always asks before these questions.
	fixedFields?: string[]
}>()
defineEmits<{ addRule: [FormQuestion] }>()

const editor = props.editor
const composer = ref<InstanceType<typeof FieldComposer> | null>(null)
const steps = useSteps(() => form.value.questions)
const hasSteps = computed(() => takesSteps(form.value.form_doctype))

const isNarrow = useBreakpoints(breakpointsTailwind).smaller("lg")
// The phone preview sits in a card on a grey canvas; on a real phone the form fills the screen.
const inCard = computed(() => props.device === "mobile" && !isNarrow.value)
const twoColumns = computed(() => props.device === "desktop" && !isNarrow.value)
// A phone gets field cards, a step navigator and an add-field sheet instead of hover tools.
const isPhone = useIsMobile()
const addSheetOpen = ref(false)

const stepRows = computed(() => {
	const { start, end } = steps.step.value
	return form.value.questions
		.map((question, index) => ({ question, index }))
		.slice(start, end)
		.filter(({ question }) => question.fieldtype !== "Page Break")
})

const selectedIndex = computed(() =>
	editor.selected.value ? editor.indexOf(editor.selected.value) : -1,
)
watch(
	() => props.preview,
	(on) => on && (editor.selected.value = null),
)

const inspectorOpen = computed({
	get: () => !props.preview && selectedIndex.value >= 0 && editor.settingsOpen.value,
	set: (open) => (editor.settingsOpen.value = open),
})
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

const doctypeFieldOf = (question: FormQuestion) =>
	question.is_standard ? props.doctypeFields[question.fieldname] : undefined

const rulesActingOn = (question: FormQuestion) =>
	form.value.logic_rules.filter((rule) =>
		rule.actions.some(([, target]) => target === question.fieldname),
	).length

const dragged = ref<FormQuestion | null>(null)
const dropIndex = ref<number | null>(null)

function onRowDragOver(index: number, event: DragEvent) {
	if (!dragged.value) return
	event.preventDefault()
	const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
	dropIndex.value = event.clientY < box.top + box.height / 2 ? index : index + 1
}

function onDrop() {
	if (dragged.value) editor.move(dragged.value, dropIndex.value ?? steps.step.value.end)
	endDrag()
}

function endDrag() {
	dragged.value = null
	dropIndex.value = null
}

// New fields land after the selected one, or at the end of the step on screen.
function addItem(item: MenuItem) {
	if (item === ADD_STEP) return steps.add()
	const selected = selectedIndex.value
	const { start, end } = steps.step.value
	const at = selected >= start && selected < end ? selected + 1 : end
	editor.insert(at, item.fields.map(newQuestion))
}

const isLastStep = computed(() => steps.stepIndex.value >= steps.steps.value.length - 1)

function isTyping(event: KeyboardEvent) {
	const target = event.target as HTMLElement
	return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
}

useEventListener(window, "dragend", endDrag)

useEventListener(window, "keydown", (event: KeyboardEvent) => {
	if (event.defaultPrevented) return
	if (event.key === "Escape") editor.selected.value = null
	if (isTyping(event) || props.preview) return
	if (event.key === "/") {
		event.preventDefault()
		composer.value?.focus()
	}
})

const header = ref<InstanceType<typeof FormHeader> | null>(null)
const rowsBox = ref<HTMLElement | null>(null)

const rowElement = (question: FormQuestion) =>
	rowsBox.value?.querySelector<HTMLElement>(`[data-row="${questionKey(question)}"]`)

// Past the first row lies the form intro, past the last the composer.
function focusRow(position: number, part: "row" | "label" = "row") {
	const rows = stepRows.value
	if (position < 0) return header.value?.focus()
	if (position >= rows.length) return composer.value?.focus()
	const row = rowElement(rows[position].question)
	;(part === "label" ? row?.querySelector<HTMLElement>("[data-label]") : row)?.focus()
}

// Moves keep a field in its step; the focus follows it, since moving a node drops focus.
function moveWithinStep(position: number, step: number) {
	const target = stepRows.value[position + step]
	if (!target) return
	const onLabel = document.activeElement?.hasAttribute("data-label")
	editor.move(stepRows.value[position].question, step < 0 ? target.index : target.index + 1)
	nextTick().then(() => focusRow(position + step, onLabel ? "label" : "row"))
}

function removeAt(position: number) {
	editor.remove(stepRows.value[position].question)
	nextTick().then(() => focusRow(Math.min(position, stepRows.value.length - 1)))
}

function closeInspector() {
	inspectorOpen.value = false
	const selected = editor.selected.value
	if (selected) rowElement(selected)?.focus()
}

const inspector = ref<HTMLElement | null>(null)
watch(inspectorOpen, (open) => open && nextTick().then(() => inspector.value?.focus()))
</script>

<template>
	<div class="relative h-full min-h-0">
		<div
			class="h-full overflow-y-auto"
			:class="
				inCard
					? 'bg-surface-gray-1 px-4 pb-20 pt-6'
					: isPhone
						? 'bg-surface-base pb-36 pt-5'
						: 'bg-surface-base pb-24 pt-6 lg:pt-12'
			"
			@click="editor.selected.value = null"
		>
			<div
				class="mx-auto w-full bg-surface-base transition-[max-width] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)]"
				:class="
					inCard
						? 'max-w-[390px] rounded-5 px-4 pb-7 pt-5 shadow-sm ring-1 ring-inset ring-outline-gray-1'
						: 'max-w-[760px] px-4 pb-12 sm:px-10'
				"
			>
				<FormHeader
					ref="header"
					v-model="form"
					:readonly="preview"
					@leave-down="focusRow(0, 'label')"
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

				<StepBar
					v-if="hasSteps && steps.steps.value.length > 1"
					:steps="steps"
					:questions="form.questions"
					:compact="isPhone"
					:tight="!twoColumns"
					:editable="!preview"
				/>

				<div
					ref="rowsBox"
					class="grid grid-cols-2"
					:class="isPhone ? 'gap-y-2' : '-mx-3 gap-y-1.5'"
					@dragover.prevent
					@drop.prevent="onDrop"
				>
					<div
						v-for="({ question, index }, position) in stepRows"
						:key="questionKey(question)"
						class="relative"
						:class="{
							'col-span-2': question.width !== 'Half' || !twoColumns,
							'opacity-40': dragged && toRaw(dragged) === toRaw(question),
						}"
						@dragover="onRowDragOver(index, $event)"
					>
						<span
							v-if="dropIndex === index"
							class="absolute inset-x-2 -top-1 h-0.5 rounded-full bg-surface-blue-6"
							aria-hidden="true"
						/>
						<FieldRow
							v-model="form.questions[index]"
							:doctype-field="doctypeFieldOf(question)"
							:editor="editor"
							:conditional="rulesActingOn(question) > 0"
							:preview="preview"
							:compact="isPhone"
							:is-first="index === 0"
							:is-last="index === form.questions.length - 1"
							:data-row="questionKey(question)"
							@dragstart="dragged = question"
							@navigate="(step, part) => focusRow(position + step, part)"
							@move="(step) => moveWithinStep(position, step)"
							@remove="removeAt(position)"
						/>
					</div>
					<div
						v-if="!preview && !isPhone"
						class="relative col-span-2 mt-1.5"
						@dragover.prevent="dropIndex = steps.step.value.end"
						@click.stop
					>
						<span
							v-if="dropIndex === steps.step.value.end"
							class="absolute inset-x-2 -top-1 h-0.5 rounded-full bg-surface-blue-6"
							aria-hidden="true"
						/>
						<FieldComposer
							ref="composer"
							:form-doctype="form.form_doctype"
							@pick="addItem"
							@leave-up="focusRow(stepRows.length - 1, 'label')"
						/>
					</div>
				</div>

				<button
					v-if="hasSteps && !preview"
					type="button"
					class="mt-8 flex w-full items-center gap-3 text-p-sm text-ink-gray-5 transition-colors hover:text-ink-gray-8"
					@click.stop="steps.add()"
				>
					<span class="flex-1 border-t border-dashed border-outline-gray-3" aria-hidden="true" />
					<span class="lucide-separator-horizontal size-4" aria-hidden="true" />
					Add a step after this
					<span class="flex-1 border-t border-dashed border-outline-gray-3" aria-hidden="true" />
				</button>

				<div class="mt-5 flex items-center gap-3" @click.stop>
					<Button
						v-if="steps.stepIndex.value > 0"
						size="lg"
						label="Back"
						@click="steps.go(steps.stepIndex.value - 1)"
					/>
					<Button
						class="flex-1"
						variant="solid"
						size="lg"
						:label="isLastStep ? form.submit_label || 'Submit' : 'Next'"
						:disabled="isLastStep"
						@click="steps.go(steps.stepIndex.value + 1)"
					/>
				</div>
			</div>
		</div>

		<Transition
			enter-from-class="translate-x-3 opacity-0"
			leave-to-class="translate-x-3 opacity-0"
			enter-active-class="transition duration-200 ease-[cubic-bezier(0.23,1,0.32,1)]"
			leave-active-class="transition duration-150 ease-[cubic-bezier(0.23,1,0.32,1)]"
		>
			<aside
				v-if="!isNarrow && inspectorOpen"
				ref="inspector"
				tabindex="-1"
				aria-label="Field settings"
				class="absolute bottom-2 right-2 top-2 z-30 w-[296px] overflow-hidden rounded-5 bg-surface-base shadow-xl outline-none ring-1 ring-outline-gray-1"
				@click.stop
				@keydown.esc.prevent="closeInspector"
			>
				<FieldInspector
					:key="questionKey(form.questions[selectedIndex])"
					v-model="form.questions[selectedIndex]"
					v-bind="inspectorProps"
					@close="closeInspector"
					@add-rule="$emit('addRule', form.questions[selectedIndex])"
				/>
			</aside>
		</Transition>
		<template v-if="isPhone && !preview">
			<Button
				variant="solid"
				size="lg"
				icon-left="lucide-plus"
				label="Add field"
				class="fixed bottom-[max(1.25rem,env(safe-area-inset-bottom))] left-1/2 z-20 -translate-x-1/2 shadow-xl"
				@click="addSheetOpen = true"
			/>
			<AddFieldSheet
				v-model:open="addSheetOpen"
				:form-doctype="form.form_doctype"
				:step-name="steps.step.value.name"
				@pick="addItem"
			/>
		</template>
		<BottomSheet v-if="isNarrow" v-model:open="inspectorOpen" title="Field settings">
			<FieldInspector
				v-if="selectedIndex >= 0"
				:key="questionKey(form.questions[selectedIndex])"
				v-model="form.questions[selectedIndex]"
				v-bind="inspectorProps"
				@close="inspectorOpen = false"
				@add-rule="$emit('addRule', form.questions[selectedIndex])"
			/>
		</BottomSheet>
	</div>
</template>
