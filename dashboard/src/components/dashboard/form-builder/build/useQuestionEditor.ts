import { ref, toRaw } from "vue"

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

export function useQuestionEditor(questions: () => FormQuestion[]) {
	const selected = ref<FormQuestion | null>(null)

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

	function remove(question: FormQuestion) {
		if (question.is_standard) return
		questions().splice(indexOf(question), 1)
		if (selected.value && toRaw(selected.value) === toRaw(question)) selected.value = null
	}

	function move(question: FormQuestion, to: number) {
		const from = indexOf(question)
		const [row] = questions().splice(from, 1)
		questions().splice(to > from ? to - 1 : to, 0, row)
	}

	function convert(question: FormQuestion, fieldtype: string) {
		if (question.label === fieldType(question.fieldtype).label)
			question.label = fieldType(fieldtype).label
		if (CHOICE_TYPES.includes(fieldtype) && !question.options) question.options = DEFAULT_OPTIONS
		question.fieldtype = fieldtype
	}

	return { selected, indexOf, insert, insertAfterSelection, duplicate, remove, move, convert }
}

export type QuestionEditor = ReturnType<typeof useQuestionEditor>
