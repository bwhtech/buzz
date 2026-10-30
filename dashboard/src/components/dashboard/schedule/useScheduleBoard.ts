import { useEventListener } from "@vueuse/core"
import { type InjectionKey, type Ref, computed, inject, provide, ref } from "vue"

import {
	HOUR_HEIGHT,
	MIN_DURATION,
	TIMELINE_RATIO,
	clamp,
	hourMarks,
	snap,
	snapDown,
} from "./scheduleLayout"
import type { DragPayload, ScheduleView } from "./scheduleTypes"
import type { ScheduleBuilder } from "./useScheduleBuilder"

type Axis = "y" | "x"

export interface Placeholder {
	track: string | null
	start: number
	duration: number
	axis: Axis
	span: boolean
}

interface QuickAddState {
	track: string | null
	start: number
	x: number
	y: number
}

const DAY_SWITCH_DELAY_MS = 750
export const pixelsPerMinute = (axis: Axis) =>
	(axis === "y" ? HOUR_HEIGHT : HOUR_HEIGHT * TIMELINE_RATIO) / 60

export function useScheduleBoard(builder: ScheduleBuilder, view: Ref<ScheduleView>) {
	const selectedKey = ref<string | null>(null)
	const quickAdd = ref<QuickAddState | null>(null)
	const placeholder = ref<Placeholder | null>(null)
	const dropDay = ref<string | null>(null)
	const panelDrop = ref(false)
	const dragKey = ref<string | null>(null)
	const dragging = ref(false)
	const tab = ref<"talks" | "custom">("talks")
	const addingTrack = ref(false)
	const renamingTrack = ref<string | null>(null)
	const trackDraft = ref("")

	const selected = computed(
		() => builder.items.value.find((item) => item.key === selectedKey.value) ?? null,
	)
	const range = computed(() => builder.rangeOf(builder.activeDate.value))
	const hours = computed(() => hourMarks(range.value))

	let drag: DragPayload | null = null
	let daySwitchTimer: ReturnType<typeof setTimeout> | undefined

	function select(key: string | null) {
		selectedKey.value = key
		quickAdd.value = null
		placeholder.value = null
	}

	function startDrag(payload: DragPayload, event: DragEvent) {
		if (resizing) return event.preventDefault()
		const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
		const isItem = payload.kind === "item"
		drag = {
			...payload,
			grabX: isItem ? event.clientX - box.left : 0,
			grabY: isItem ? event.clientY - box.top : 0,
		}
		event.dataTransfer?.setData("text/plain", payload.id)
		if (event.dataTransfer) event.dataTransfer.effectAllowed = "move"
		setTimeout(() => {
			dragKey.value = isItem ? payload.id : null
			dragging.value = true
			quickAdd.value = null
		})
	}

	function endDrag() {
		drag = null
		clearTimeout(daySwitchTimer)
		dragKey.value = null
		dragging.value = false
		placeholder.value = null
		dropDay.value = null
		panelDrop.value = false
	}

	function startFrom(event: DragEvent | MouseEvent, axis: Axis) {
		const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
		const grab = axis === "y" ? (drag?.grabY ?? 0) : (drag?.grabX ?? 0)
		const offset = (axis === "y" ? event.clientY - box.top : event.clientX - box.left) - grab
		const minutes = snap(range.value.start + offset / pixelsPerMinute(axis))
		return clamp(minutes, range.value.start, range.value.end - (drag?.duration ?? MIN_DURATION))
	}

	const dragOver = (track: string | null, axis: Axis) => (event: DragEvent) => {
		if (!drag) return
		event.preventDefault()
		const start = startFrom(event, axis)
		const current = placeholder.value
		if (current && current.track === track && current.start === start && current.axis === axis)
			return
		placeholder.value = { track, start, duration: drag.duration, axis, span: drag.span }
		dropDay.value = null
	}

	const dropOn = (track: string | null) => (event: DragEvent) => {
		event.preventDefault()
		const placed =
			drag &&
			placeholder.value &&
			builder.place(drag, builder.activeDate.value, track, placeholder.value.start)
		if (placed && placed.type === "Custom") selectedKey.value = placed.key
		endDrag()
	}

	function clickSlot(track: string | null, axis: Axis) {
		return (event: MouseEvent) => {
			if (event.target !== event.currentTarget) return
			const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
			const offset = axis === "y" ? event.clientY - box.top : event.clientX - box.left
			const raw = range.value.start + offset / pixelsPerMinute(axis)
			const start = Math.min(snapDown(raw), range.value.end - 30)
			quickAdd.value = { track, start, x: event.clientX, y: event.clientY }
			selectedKey.value = null
			placeholder.value = { track, start, duration: 30, axis, span: false }
		}
	}

	const dayOver = (date: string) => (event: DragEvent) => {
		if (!drag) return
		event.preventDefault()
		if (dropDay.value === date) return
		dropDay.value = date
		placeholder.value = null
		clearTimeout(daySwitchTimer)
		if (date === builder.activeDate.value) return
		daySwitchTimer = setTimeout(
			() => drag && (builder.activeDate.value = date),
			DAY_SWITCH_DELAY_MS,
		)
	}

	function dayLeave(event: DragEvent) {
		if ((event.currentTarget as HTMLElement).contains(event.relatedTarget as Node)) return
		clearTimeout(daySwitchTimer)
		dropDay.value = null
	}

	const dayDrop = (date: string) => (event: DragEvent) => {
		event.preventDefault()
		clearTimeout(daySwitchTimer)
		if (drag) builder.place(drag, date)
		endDrag()
	}

	function panelOver(event: DragEvent) {
		if (drag?.kind !== "item") return
		event.preventDefault()
		panelDrop.value = true
		placeholder.value = null
	}

	function panelLeave(event: DragEvent) {
		if (!(event.currentTarget as HTMLElement).contains(event.relatedTarget as Node))
			panelDrop.value = false
	}

	function panelDropped(event: DragEvent) {
		event.preventDefault()
		if (drag?.kind === "item") builder.remove(drag.id)
		endDrag()
	}

	let resizing: {
		key: string
		axis: Axis
		origin: number
		duration: number
		start: number
	} | null = null
	const startResize = (key: string, axis: Axis) => (event: MouseEvent) => {
		event.stopPropagation()
		event.preventDefault()
		const item = builder.findItem(key)
		if (!item) return
		builder.saveUndoPoint()
		const origin = axis === "y" ? event.clientY : event.clientX
		resizing = { key, axis, origin, duration: item.duration, start: item.start }
	}
	useEventListener(window, "mousemove", (event: MouseEvent) => {
		if (!resizing) return
		const pointer = resizing.axis === "y" ? event.clientY : event.clientX
		const moved = (pointer - resizing.origin) / pixelsPerMinute(resizing.axis)
		const longest = range.value.end - resizing.start
		const duration = Math.min(longest, snap(resizing.duration + moved))
		builder.resize(resizing.key, duration)
	})
	useEventListener(window, "mouseup", () => resizing && setTimeout(() => (resizing = null)))

	useEventListener(window, "keydown", (event: KeyboardEvent) => {
		const field = (event.target as HTMLElement).tagName?.toLowerCase()
		const typing = ["input", "textarea", "select"].includes(field)
		if (event.key === "Escape") {
			quickAdd.value = null
			placeholder.value = null
			addingTrack.value = false
			renamingTrack.value = null
			if (!typing) selectedKey.value = null
		}
		const removing = event.key === "Backspace" || event.key === "Delete"
		if (!typing && removing && selectedKey.value) builder.remove(selectedKey.value)
	})

	const board = {
		view,
		selectedKey,
		selected,
		quickAdd,
		placeholder,
		dropDay,
		panelDrop,
		dragKey,
		dragging,
		tab,
		range,
		hours,
		addingTrack,
		renamingTrack,
		trackDraft,
		select,
		startDrag,
		endDrag,
		dragOver,
		dropOn,
		clickSlot,
		dayOver,
		dayLeave,
		dayDrop,
		panelOver,
		panelLeave,
		panelDropped,
		startResize,
	}
	return board
}

export type ScheduleBoard = ReturnType<typeof useScheduleBoard>
const builderKey: InjectionKey<ScheduleBuilder> = Symbol("scheduleBuilder")
const boardKey: InjectionKey<ScheduleBoard> = Symbol("scheduleBoard")

export function provideSchedule(builder: ScheduleBuilder, board: ScheduleBoard) {
	provide(builderKey, builder)
	provide(boardKey, board)
}

export const useBuilder = () => inject(builderKey)!
export const useBoard = () => inject(boardKey)!
