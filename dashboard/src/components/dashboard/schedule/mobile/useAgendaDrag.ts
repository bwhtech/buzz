import { useEventListener } from "@vueuse/core"
import { onBeforeUnmount, ref } from "vue"

import { clock } from "../scheduleLayout"
import type { ScheduleItem } from "../scheduleTypes"
import { useBoard, useBuilder } from "../useScheduleBoard"

export interface AgendaDrag {
	key: string
	offset: number
	target: number | null
}

function slotAt(x: number, y: number) {
	const row = document
		.elementsFromPoint(x, y)
		.find((element) => element instanceof HTMLElement && element.dataset.dropStart)
	return row instanceof HTMLElement ? Number(row.dataset.dropStart) : null
}

/** The grip of a list card drags it onto a time slot or a free gap, which sets its start. */
export function useAgendaDrag() {
	const builder = useBuilder()
	const board = useBoard()
	const drag = ref<AgendaDrag | null>(null)
	let originY = 0
	let stopListening: Array<() => void> = []

	function begin(event: PointerEvent, item: ScheduleItem) {
		if (event.button) return
		event.stopPropagation()
		finish()
		originY = event.clientY
		drag.value = { key: item.key, offset: 0, target: null }
		stopListening = [
			useEventListener(window, "pointermove", onMove, { passive: false }),
			useEventListener(window, "pointerup", onEnd),
			useEventListener(window, "pointercancel", finish),
		]
	}

	function onMove(event: PointerEvent) {
		if (!drag.value) return
		event.preventDefault()
		const offset = event.clientY - originY
		drag.value = { ...drag.value, offset, target: slotAt(event.clientX, event.clientY) }
	}

	function onEnd() {
		const ended = drag.value
		finish()
		const item = builder.items.value.find((entry) => entry.key === ended?.key)
		if (!item || ended?.target == null) return
		const { start: first, end } = board.range.value
		const start = Math.max(first, Math.min(end - item.duration, ended.target))
		if (start !== item.start) builder.update(item.key, { start }, `Moved to ${clock(start)}`)
	}

	function finish() {
		drag.value = null
		stopListening.forEach((stop) => stop())
		stopListening = []
	}

	onBeforeUnmount(finish)
	return { drag, begin }
}
