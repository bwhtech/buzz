import { ref, toRaw, watch } from "vue"

import type { LogicRule } from "@/utils/formLogic"

import { CHOICE_TYPES, fieldType, type PresetField } from "../fieldTypes"
import type { FormQuestion } from "../useFormBuilder"

// What a question carries into a copy; the server names and numbers the new row.
const COPIED_FIELDS = [
	"label",
	"fieldtype",
	"options",
	"placeholder",
	"description",
	"width",
] as const

const DEFAULT_OPTIONS = "Option 1\nOption 2\nOption 3"

const keys = new WeakMap<object, number>()
let lastKey = 0

// Rows have no name until saved, so the list keys them by identity.
export function questionKey(question: FormQuestion): number {
	const raw = toRaw(question)
	if (!keys.has(raw)) keys.set(raw, ++lastKey)
	return keys.get(raw)!
}

export function newQuestion(field: PresetField): FormQuestion {
	return {
		fieldname: "",
		enabled: 1,
		mandatory: 0,
		width: "Full",
		options: CHOICE_TYPES.includes(field.fieldtype) ? DEFAULT_OPTIONS : null,
		...field,
	}
}

// A rule needs a name for the question before the server would give it one on save.
function fieldnameFrom(label: string, taken: Set<string>): string {
	let name = label
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "_")
		.replace(/^_+|_+$/g, "")
	if (!/^[a-z]/.test(name)) name = `question_${name}`
	let candidate = name
	for (let suffix = 2; taken.has(candidate); suffix++) candidate = `${name}_${suffix}`
	return candidate
}

// A paragraph keeps its words in rich text, a heading in its label.
function moveParagraphText(question: FormQuestion, fieldtype: string) {
	if (question.fieldtype === "Paragraph") {
		const text = new DOMParser().parseFromString(question.description || "", "text/html").body
		question.label = text.textContent?.trim() || question.label
		question.description = null
	} else if (fieldtype === "Paragraph") {
		question.description = question.label
		question.label = fieldType(fieldtype).label
	}
}

export function useQuestionEditor(questions: () => FormQuestion[], rules: () => LogicRule[]) {
	const selected = ref<FormQuestion | null>(null)
	// On a phone, settings open as a sheet only when asked for, so tapping a label edits it.
	const settingsOpen = ref(false)
	watch(selected, (question) => question || (settingsOpen.value = false))

	const indexOf = (question: FormQuestion) =>
		questions().findIndex((row) => toRaw(row) === toRaw(question))

	function insert(at: number, added: FormQuestion[]) {
		questions().splice(at, 0, ...added)
		selected.value = questions()[at]
	}

	function insertAfterSelection(added: FormQuestion[]) {
		insert(selected.value ? indexOf(selected.value) + 1 : questions().length, added)
	}

	function duplicate(question: FormQuestion) {
		const copy = Object.fromEntries(COPIED_FIELDS.map((key) => [key, question[key]]))
		insert(indexOf(question) + 1, [
			newQuestion({ ...copy, label: `${question.label} copy` } as PresetField),
		])
	}

	function ensureFieldname(question: FormQuestion): string {
		if (!question.fieldname) {
			const taken = new Set(
				questions()
					.map((row) => row.fieldname)
					.filter(Boolean),
			)
			question.fieldname = fieldnameFrom(question.label || question.fieldtype, taken)
		}
		return question.fieldname
	}

	// A deleted question takes its conditions and actions along; a rule it emptied goes too.
	function dropFromRules(fieldname: string) {
		const kept = rules()
			.map((rule) => ({
				rule: {
					...rule,
					conditions: rule.conditions.filter(([name]) => name !== fieldname),
					actions: rule.actions.filter(([, target]) => target !== fieldname),
				},
				hadConditions: rule.conditions.length > 0,
			}))
			.filter(
				({ rule, hadConditions }) =>
					rule.actions.length && (rule.conditions.length || !hadConditions),
			)
			.map(({ rule }) => rule)
		rules().splice(0, rules().length, ...kept)
	}

	function remove(question: FormQuestion) {
		if (question.is_standard) return
		if (question.fieldname) dropFromRules(question.fieldname)
		questions().splice(indexOf(question), 1)
		if (selected.value && toRaw(selected.value) === toRaw(question)) selected.value = null
	}

	function move(question: FormQuestion, to: number) {
		const from = indexOf(question)
		const [row] = questions().splice(from, 1)
		questions().splice(to > from ? to - 1 : to, 0, row)
	}

	function convert(question: FormQuestion, fieldtype: string) {
		moveParagraphText(question, fieldtype)
		if (question.label === fieldType(question.fieldtype).label)
			question.label = fieldType(fieldtype).label
		if (CHOICE_TYPES.includes(fieldtype) && !question.options) question.options = DEFAULT_OPTIONS
		question.fieldtype = fieldtype
	}

	return {
		selected,
		settingsOpen,
		indexOf,
		insert,
		insertAfterSelection,
		duplicate,
		remove,
		move,
		convert,
		ensureFieldname,
	}
}

export type QuestionEditor = ReturnType<typeof useQuestionEditor>
