import { ref, toRaw } from "vue"

import { fieldType } from "../fieldTypes"
import type { FormQuestion } from "../useFormBuilder"
import type { QuestionEditor } from "./useQuestionEditor"

export type DropEdge = "top" | "bottom" | "left" | "right" | "swap"

interface StepRow {
	question: FormQuestion
	index: number
}

export const DROP_LINE_CLASSES: Record<Exclude<DropEdge, "swap">, string> = {
	top: "inset-x-2 -top-1 h-0.5",
	bottom: "inset-x-2 -bottom-1 h-0.5",
	left: "inset-y-2 -left-0.5 w-0.5",
	right: "inset-y-2 -right-0.5 w-0.5",
}

const isLayout = (question: FormQuestion) => fieldType(question.fieldtype).group === "Layout"
const same = (one?: FormQuestion | null, other?: FormQuestion | null) =>
	!!one && !!other && toRaw(one) === toRaw(other)

// Half-width fields pair up in order, two to a row; a full-width field ends the row.
function partnersOf(rows: StepRow[], skipped: FormQuestion | null) {
	const partners = new Map<FormQuestion, FormQuestion>()
	let open: FormQuestion | null = null
	for (const { question } of rows) {
		const raw = toRaw(question)
		if (same(raw, skipped)) continue
		if (raw.width !== "Half") open = null
		else if (open) {
			partners.set(open, raw)
			partners.set(raw, open)
			open = null
		} else open = raw
	}
	return partners
}

// Edges insert above, below or beside a field; its middle swaps the two fields' places.
export function useCanvasDrag(
	rows: () => StepRow[],
	questions: () => FormQuestion[],
	editor: QuestionEditor,
	twoColumns: () => boolean,
) {
	const dragged = ref<FormQuestion | null>(null)
	const drop = ref<{ index: number; edge: DropEdge } | null>(null)

	const partnerOf = (question: FormQuestion, skipped = dragged.value) =>
		partnersOf(rows(), skipped).get(toRaw(question))

	function canSitBeside(target: FormQuestion) {
		const question = dragged.value!
		return twoColumns() && !isLayout(question) && !isLayout(target) && !partnerOf(target)
	}

	const canSwap = (target: FormQuestion) =>
		dragged.value!.width === target.width || !(isLayout(dragged.value!) || isLayout(target))

	function edgeAt(event: DragEvent, target: FormQuestion): DropEdge {
		const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
		const x = (event.clientX - box.left) / box.width
		const y = (event.clientY - box.top) / box.height
		if ((x < 0.2 || x > 0.8) && canSitBeside(target)) return x < 0.2 ? "left" : "right"
		if (y > 0.3 && y < 0.7 && canSwap(target)) return "swap"
		return y < 0.5 ? "top" : "bottom"
	}

	function start(question: FormQuestion, event: DragEvent) {
		dragged.value = question
		if (!event.dataTransfer) return
		event.dataTransfer.effectAllowed = "move"
		// Firefox only starts a drag that carries data.
		event.dataTransfer.setData("text/plain", "")
	}

	function over({ question, index }: StepRow, event: DragEvent) {
		if (!dragged.value) return
		event.preventDefault()
		if (event.dataTransfer) event.dataTransfer.dropEffect = "move"
		drop.value = same(question, dragged.value) ? null : { index, edge: edgeAt(event, question) }
	}

	const overEnd = (stepEnd: number) =>
		dragged.value && (drop.value = { index: stepEnd, edge: "top" })

	function swap(question: FormQuestion, target: FormQuestion) {
		const [from, to] = [editor.indexOf(question), editor.indexOf(target)]
		;[question.width, target.width] = [target.width, question.width]
		questions().splice(from, 1, target)
		questions().splice(to, 1, question)
	}

	// The pair can be split by a lone half-width field just before it, which then takes the row.
	function sitBeside(question: FormQuestion, index: number, edge: DropEdge) {
		const target = questions()[index]
		question.width = target.width = "Half"
		editor.move(question, edge === "left" ? index : index + 1)
		const left = Math.min(editor.indexOf(question), editor.indexOf(target))
		if (!same(partnerOf(target, null), question)) questions()[left - 1].width = "Full"
	}

	// Above or below a pair means above or below its whole row.
	function insertAround(question: FormQuestion, index: number, edge: DropEdge) {
		const target = questions()[index]
		const partner = target ? partnerOf(target) : undefined
		const ends = [index, partner ? editor.indexOf(partner) : index]
		question.width = "Full"
		editor.move(question, edge === "top" ? Math.min(...ends) : Math.max(...ends) + 1)
	}

	function place() {
		const question = dragged.value
		const target = drop.value
		if (!question || !target) return end()
		const formerPartner = partnerOf(question, null)
		const joined = ["left", "right"].includes(target.edge) ? questions()[target.index] : null
		if (target.edge === "swap") swap(question, questions()[target.index])
		else if (target.edge === "left" || target.edge === "right")
			sitBeside(question, target.index, target.edge)
		else insertAround(question, target.index, target.edge)
		if (target.edge !== "swap" && formerPartner && !same(formerPartner, joined))
			formerPartner.width = "Full"
		end()
	}

	function end() {
		dragged.value = null
		drop.value = null
	}

	const edgeOn = (index: number) => (drop.value?.index === index ? drop.value.edge : null)

	return { dragged, start, over, overEnd, place, end, edgeOn }
}
