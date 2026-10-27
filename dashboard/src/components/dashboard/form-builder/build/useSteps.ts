import { computed, ref } from "vue"

import type { FormQuestion } from "../useFormBuilder"
import { newQuestion } from "./useQuestionEditor"

export interface Step {
	name: string
	// Index of the page break that opens the step, or -1 for a first step with no name yet.
	breakIndex: number
	start: number
	end: number
}

// Page breaks split the questions into steps; the canvas shows one step at a time.
export function useSteps(questions: () => FormQuestion[]) {
	const current = ref(0)

	const steps = computed<Step[]>(() => {
		const rows = questions()
		const list: Step[] = []
		if (rows[0]?.fieldtype !== "Page Break")
			list.push({ name: "", breakIndex: -1, start: 0, end: 0 })
		rows.forEach((row, index) => {
			if (row.fieldtype !== "Page Break") return
			if (list.length) list[list.length - 1].end = index
			list.push({ name: row.label, breakIndex: index, start: index + 1, end: 0 })
		})
		list[list.length - 1].end = rows.length
		return list
	})
	const step = computed(() => steps.value[Math.min(current.value, steps.value.length - 1)])
	const stepIndex = computed(() => steps.value.indexOf(step.value))

	function rename(name: string) {
		if (step.value.breakIndex >= 0) questions()[step.value.breakIndex].label = name
		else questions().unshift(pageBreak(name))
	}

	function add() {
		questions().splice(step.value.end, 0, pageBreak("Untitled step"))
		current.value = stepIndex.value + 1
	}

	// The step's questions join the one before it.
	function remove() {
		if (step.value.breakIndex < 0) return
		questions().splice(step.value.breakIndex, 1)
		current.value = Math.max(0, stepIndex.value - 1)
	}

	const go = (index: number) => (current.value = index)

	return { steps, step, stepIndex, rename, add, remove, go }
}

const pageBreak = (label: string) => newQuestion({ fieldtype: "Page Break", label })

export type Steps = ReturnType<typeof useSteps>
