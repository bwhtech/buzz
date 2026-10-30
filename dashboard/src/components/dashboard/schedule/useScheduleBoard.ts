import { useEventListener } from "@vueuse/core"
import { type InjectionKey, type Ref, computed, inject, provide, ref } from "vue"

import { MIN_DURATION, SNAP_MINUTES, TIMELINE_RATIO, ZOOM, snap } from "./scheduleLayout"
import type { DragPayload, ScheduleView } from "./scheduleTypes"
import type { ScheduleBuilder } from "./useScheduleBuilder"

type Axis = "y" | "x"

export interface Ghost {
	room: string | null
	start: number
	duration: number
	axis: Axis
	span: boolean
}

interface Quick {
	room: string | null
	start: number
	x: number
	y: number
}

const DAY_SPRING_MS = 750
export const pixelsPerMinute = (axis: Axis) => (axis === "y" ? ZOOM : ZOOM * TIMELINE_RATIO) / 60

export function useScheduleBoard(builder: ScheduleBuilder, view: Ref<ScheduleView>) {
	const selectedKey = ref<string | null>(null)
	const quick = ref<Quick | null>(null)
	const ghost = ref<Ghost | null>(null)
	const dropDay = ref<string | null>(null)
	const panelDrop = ref(false)
	const dragKey = ref<string | null>(null)
	const dragging = ref(false)
	const tab = ref<"talks" | "custom">("talks")
	const addingRoom = ref(false)
	const renamingRoom = ref<string | null>(null)
	const roomDraft = ref("")

	const selected = computed(
		() => builder.items.value.find((item) => item.key === selectedKey.value) ?? null,
	)
	const range = computed(() => builder.rangeOf(builder.activeDate.value))

	let drag: DragPayload | null = null
	let springTimer: ReturnType<typeof setTimeout> | undefined

	function select(key: string | null) {
		selectedKey.value = key
		quick.value = null
		ghost.value = null
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
			quick.value = null
		})
	}

	function endDrag() {
		drag = null
		clearTimeout(springTimer)
		dragKey.value = null
		dragging.value = false
		ghost.value = null
		dropDay.value = null
		panelDrop.value = false
	}

	function startFrom(event: DragEvent | MouseEvent, axis: Axis) {
		const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
		const grab = axis === "y" ? (drag?.grabY ?? 0) : (drag?.grabX ?? 0)
		const offset = (axis === "y" ? event.clientY - box.top : event.clientX - box.left) - grab
		const minutes = snap(range.value.start + offset / pixelsPerMinute(axis))
		return Math.max(
			range.value.start,
			Math.min(range.value.end - (drag?.duration ?? MIN_DURATION), minutes),
		)
	}

	const dragOver = (room: string | null, axis: Axis) => (event: DragEvent) => {
		if (!drag) return
		event.preventDefault()
		const start = startFrom(event, axis)
		const current = ghost.value
		if (current && current.room === room && current.start === start && current.axis === axis) return
		ghost.value = { room, start, duration: drag.duration, axis, span: drag.span }
		dropDay.value = null
	}

	const dropOn = (room: string | null) => (event: DragEvent) => {
		event.preventDefault()
		const placed =
			drag && ghost.value && builder.place(drag, builder.activeDate.value, room, ghost.value.start)
		if (placed && placed.type === "Custom") selectedKey.value = placed.key
		endDrag()
	}

	function clickSlot(room: string | null, axis: Axis) {
		return (event: MouseEvent) => {
			if (event.target !== event.currentTarget) return
			const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
			const offset = axis === "y" ? event.clientY - box.top : event.clientX - box.left
			const raw = range.value.start + offset / pixelsPerMinute(axis)
			const start = Math.min(Math.floor(raw / SNAP_MINUTES) * SNAP_MINUTES, range.value.end - 30)
			quick.value = { room, start, x: event.clientX, y: event.clientY }
			selectedKey.value = null
			ghost.value = { room, start, duration: 30, axis, span: false }
		}
	}

	const dayOver = (date: string) => (event: DragEvent) => {
		if (!drag) return
		event.preventDefault()
		if (dropDay.value === date) return
		dropDay.value = date
		ghost.value = null
		clearTimeout(springTimer)
		if (date === builder.activeDate.value) return
		springTimer = setTimeout(() => drag && (builder.activeDate.value = date), DAY_SPRING_MS)
	}

	function dayLeave(event: DragEvent) {
		if ((event.currentTarget as HTMLElement).contains(event.relatedTarget as Node)) return
		clearTimeout(springTimer)
		dropDay.value = null
	}

	const dayDrop = (date: string) => (event: DragEvent) => {
		event.preventDefault()
		clearTimeout(springTimer)
		if (drag) builder.place(drag, date)
		endDrag()
	}

	function panelOver(event: DragEvent) {
		if (drag?.kind !== "item") return
		event.preventDefault()
		panelDrop.value = true
		ghost.value = null
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
		const item = builder.items.value.find((entry) => entry.key === key)
		if (!item) return
		builder.remember()
		const origin = axis === "y" ? event.clientY : event.clientX
		resizing = { key, axis, origin, duration: item.duration, start: item.start }
	}
	useEventListener(window, "mousemove", (event: MouseEvent) => {
		if (!resizing) return
		const pointer = resizing.axis === "y" ? event.clientY : event.clientX
		const moved = (pointer - resizing.origin) / pixelsPerMinute(resizing.axis)
		const longest = range.value.end - resizing.start
		const duration = Math.min(
			longest,
			Math.round((resizing.duration + moved) / SNAP_MINUTES) * SNAP_MINUTES,
		)
		builder.resize(resizing.key, duration)
	})
	useEventListener(window, "mouseup", () => resizing && setTimeout(() => (resizing = null)))

	useEventListener(window, "keydown", (event: KeyboardEvent) => {
		const field = (event.target as HTMLElement).tagName?.toLowerCase()
		const typing = ["input", "textarea", "select"].includes(field)
		if (event.key === "Escape") {
			quick.value = null
			ghost.value = null
			addingRoom.value = false
			renamingRoom.value = null
			if (!typing) selectedKey.value = null
		}
		const removing = event.key === "Backspace" || event.key === "Delete"
		if (!typing && removing && selectedKey.value) builder.remove(selectedKey.value)
	})

	const board = {
		view,
		selectedKey,
		selected,
		quick,
		ghost,
		dropDay,
		panelDrop,
		dragKey,
		dragging,
		tab,
		range,
		addingRoom,
		renamingRoom,
		roomDraft,
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
