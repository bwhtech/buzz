import { useEventListener } from "@vueuse/core"
import { type Ref, onBeforeUnmount, ref } from "vue"

import { clock, durationLabel, MIN_DURATION } from "../scheduleLayout"
import type { ScheduleItem } from "../scheduleTypes"
import { useBoard, useBuilder } from "../useScheduleBoard"
import { useMobile } from "./useScheduleMobile"

export type DragMode = "move" | "resize"

export interface DragPosition {
	key: string
	start: number
	room: string | null
	duration: number
}

interface Gesture {
	origin: { x: number; y: number }
	item: DragPosition
	mode: DragMode
	moved: boolean
}

const STEP_MINUTES = 5
const stepped = (minutes: number) => Math.round(minutes / STEP_MINUTES) * STEP_MINUTES

/** A block's side grip moves it and its bottom handle resizes it; both start at once. */
export function useScheduleTouchDrag(pixelsPerMinute: number, columnWidth: Ref<number | null>) {
	const builder = useBuilder()
	const board = useBoard()
	const mobile = useMobile()
	const position = ref<DragPosition | null>(null)
	let gesture: Gesture | null = null
	let stopListening: Array<() => void> = []

	function begin(event: PointerEvent, item: ScheduleItem, mode: DragMode) {
		if (event.button) return
		event.stopPropagation()
		finish()
		const start = { key: item.key, start: item.start, room: item.room, duration: item.duration }
		gesture = {
			origin: { x: event.clientX, y: event.clientY },
			item: start,
			mode,
			moved: false,
		}
		position.value = start
		listen()
	}

	function listen() {
		stopListening = [
			useEventListener(window, "pointermove", onMove, { passive: false }),
			useEventListener(window, "pointerup", onEnd),
			useEventListener(window, "pointercancel", finish),
		]
	}

	function onMove(event: PointerEvent) {
		if (!gesture) return
		const dx = event.clientX - gesture.origin.x
		const dy = event.clientY - gesture.origin.y
		gesture.moved = true
		event.preventDefault()
		position.value = gesture.mode === "resize" ? resizedBy(dy) : movedBy(dx, dy)
	}

	function resizedBy(dy: number): DragPosition {
		const { item } = gesture!
		const longest = board.range.value.end - item.start
		const duration = stepped(item.duration + dy / pixelsPerMinute)
		return { ...item, duration: Math.max(MIN_DURATION, Math.min(longest, duration)) }
	}

	function movedBy(dx: number, dy: number): DragPosition {
		const { item } = gesture!
		const { start: first, end } = board.range.value
		const start = stepped(item.start + dy / pixelsPerMinute)
		return {
			...item,
			start: Math.max(first, Math.min(end - item.duration, start)),
			room: roomAfter(item.room, dx),
		}
	}

	function roomAfter(room: string | null, dx: number) {
		const width = columnWidth.value
		if (!room || !width || mobile.view.value !== "grid") return room
		const rooms = builder.rooms.rooms.value
		const index = rooms.findIndex((entry) => entry.name === room)
		const next = Math.max(0, Math.min(rooms.length - 1, index + Math.round(dx / width)))
		return rooms[next]?.name ?? room
	}

	function onEnd() {
		const ended = gesture
		const target = position.value
		finish()
		if (!ended) return
		if (ended.moved && target) commit(ended, target)
	}

	function commit(ended: Gesture, target: DragPosition) {
		const { item } = ended
		if (
			target.start === item.start &&
			target.room === item.room &&
			target.duration === item.duration
		)
			return
		const patch = { start: target.start, room: target.room, duration: target.duration }
		builder.update(item.key, patch, messageFor(ended.mode, target))
	}

	function messageFor(mode: DragMode, target: DragPosition) {
		if (mode === "resize") return `Length set to ${durationLabel(target.duration)}`
		const room = target.room ? ` · ${builder.rooms.titleOf(target.room)}` : ""
		return `Moved to ${clock(target.start)}${room}`
	}

	function finish() {
		gesture = null
		position.value = null
		stopListening.forEach((stop) => stop())
		stopListening = []
	}

	onBeforeUnmount(finish)
	return { position, begin }
}
