import { useEventListener } from "@vueuse/core"
import { type Ref, computed, onBeforeUnmount, ref } from "vue"

import { clock, durationLabel, MIN_DURATION } from "../scheduleLayout"
import type { ScheduleItem } from "../scheduleTypes"
import { useBoard, useBuilder } from "../useScheduleBoard"
import { useMobile } from "./useScheduleMobile"

export type DragMode = "move" | "resize"

export interface DragPosition {
	key: string
	start: number
	track: string | null
	duration: number
}

interface Point {
	x: number
	y: number
}

interface Gesture {
	origin: Point
	last: Point
	scrolled: { left: number; top: number }
	item: DragPosition
	mode: DragMode
	moved: boolean
}

const STEP_MINUTES = 5
const EDGE_PX = 56
const SIDEWAYS_PX = 24
const MAX_SCROLL_PX = 14
const roundToStep = (minutes: number) => Math.round(minutes / STEP_MINUTES) * STEP_MINUTES

/** Scroll speed for a pointer near either end of the visible band; 0 in the middle. */
function edgeScrollSpeed(pointer: number, near: number, far: number) {
	if (pointer < near + EDGE_PX)
		return -Math.min(1, (near + EDGE_PX - pointer) / EDGE_PX) * MAX_SCROLL_PX
	if (pointer > far - EDGE_PX)
		return Math.min(1, (pointer - (far - EDGE_PX)) / EDGE_PX) * MAX_SCROLL_PX
	return 0
}

/** A block's side grip moves it and its bottom handle resizes it; both start at once. */
export function useScheduleTouchDrag(
	pixelsPerMinute: number,
	columnWidth: Ref<number | null>,
	scroller: Ref<HTMLElement | null>,
	insets: Ref<{ top: number; left: number }>,
) {
	const builder = useBuilder()
	const board = useBoard()
	const mobile = useMobile()
	const position = ref<DragPosition | null>(null)
	const offset = ref<Point>({ x: 0, y: 0 })
	const activeMode = ref<DragMode | null>(null)
	const moving = computed(() => (activeMode.value === "move" ? position.value : null))
	let frame = 0
	let gesture: Gesture | null = null
	let stopListening: Array<() => void> = []

	function begin(event: PointerEvent, item: ScheduleItem, pressed: DragMode) {
		if (event.button) return
		event.stopPropagation()
		finish()
		const start = { key: item.key, start: item.start, track: item.track, duration: item.duration }
		const box = scroller.value
		gesture = {
			origin: { x: event.clientX, y: event.clientY },
			last: { x: event.clientX, y: event.clientY },
			scrolled: { left: box?.scrollLeft ?? 0, top: box?.scrollTop ?? 0 },
			item: start,
			mode: pressed,
			moved: false,
		}
		position.value = start
		activeMode.value = pressed
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
		gesture.last = { x: event.clientX, y: event.clientY }
		gesture.moved = true
		event.preventDefault()
		updatePosition()
		if (!frame) frame = requestAnimationFrame(autoScroll)
	}

	// The drag distance includes what the list scrolled since the press.
	function updatePosition() {
		if (!gesture) return
		const box = scroller.value
		const dx =
			gesture.last.x - gesture.origin.x + (box ? box.scrollLeft - gesture.scrolled.left : 0)
		const dy = gesture.last.y - gesture.origin.y + (box ? box.scrollTop - gesture.scrolled.top : 0)
		if (gesture.mode === "resize") {
			offset.value = { x: 0, y: dy }
			return void (position.value = resizedBy(dy))
		}
		const { x, y } = clampToDay(dx, dy)
		offset.value = { x, y }
		position.value = movedBy(x, y)
	}

	// A block dragged past the day would stretch the scroll area and keep it scrolling.
	function clampToDay(dx: number, dy: number): Point {
		const { item } = gesture!
		const { start: first, end } = board.range.value
		const y = Math.max(
			(first - item.start) * pixelsPerMinute,
			Math.min((end - item.start - item.duration) * pixelsPerMinute, dy),
		)
		const width = columnWidth.value
		const tracks = builder.tracks.tracks.value
		const index = tracks.findIndex((entry) => entry.name === item.track)
		if (!width || index < 0 || mobile.view.value !== "grid") return { x: 0, y }
		return { x: Math.max(-index * width, Math.min((tracks.length - 1 - index) * width, dx)), y }
	}

	// The grip sits at a block's right edge, so only a finger dragged sideways scrolls sideways.
	const isDraggingSideways = () => Math.abs(offset.value.x) > SIDEWAYS_PX

	function autoScroll() {
		frame = 0
		const box = scroller.value
		if (!gesture || !box) return
		const rect = box.getBoundingClientRect()
		const left = isDraggingSideways()
			? edgeScrollSpeed(gesture.last.x, rect.left + insets.value.left, rect.right)
			: 0
		const top = edgeScrollSpeed(gesture.last.y, rect.top + insets.value.top, rect.bottom)
		if (!left && !top) return
		box.scrollBy({ left: gesture.mode === "resize" ? 0 : left, top })
		updatePosition()
		frame = requestAnimationFrame(autoScroll)
	}

	function resizedBy(dy: number): DragPosition {
		const { item } = gesture!
		const longest = board.range.value.end - item.start
		const duration = roundToStep(item.duration + dy / pixelsPerMinute)
		return { ...item, duration: Math.max(MIN_DURATION, Math.min(longest, duration)) }
	}

	function movedBy(dx: number, dy: number): DragPosition {
		const { item } = gesture!
		const { start: first, end } = board.range.value
		const start = roundToStep(item.start + dy / pixelsPerMinute)
		return {
			...item,
			start: Math.max(first, Math.min(end - item.duration, start)),
			track: trackAfter(item.track, dx),
		}
	}

	function trackAfter(track: string | null, dx: number) {
		const width = columnWidth.value
		if (!track || !width || mobile.view.value !== "grid") return track
		const tracks = builder.tracks.tracks.value
		const index = tracks.findIndex((entry) => entry.name === track)
		const next = Math.max(0, Math.min(tracks.length - 1, index + Math.round(dx / width)))
		return tracks[next]?.name ?? track
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
			target.track === item.track &&
			target.duration === item.duration
		)
			return
		const patch = { start: target.start, track: target.track, duration: target.duration }
		builder.update(item.key, patch, messageFor(ended.mode, target))
	}

	function messageFor(mode: DragMode, target: DragPosition) {
		if (mode === "resize") return `Length set to ${durationLabel(target.duration)}`
		const track = target.track ? ` · ${builder.tracks.titleOf(target.track)}` : ""
		return `Moved to ${clock(target.start)}${track}`
	}

	function finish() {
		cancelAnimationFrame(frame)
		frame = 0
		gesture = null
		position.value = null
		activeMode.value = null
		offset.value = { x: 0, y: 0 }
		stopListening.forEach((stop) => stop())
		stopListening = []
	}

	onBeforeUnmount(finish)
	return { position, moving, offset, begin }
}
