import { computed } from "vue"

import { lanesOf } from "./scheduleLayout"
import { useBoard, useBuilder } from "./useScheduleBoard"

/** The active day's items arranged for a grid of rooms. */
export function useDayLayout() {
	const builder = useBuilder()
	const board = useBoard()
	const rooms = builder.rooms.rooms
	const dayItems = computed(() => builder.dayItems(builder.activeDate.value))
	const roomIndex = computed(() =>
		Object.fromEntries(rooms.value.map((room, index) => [room.name, index])),
	)
	const visible = computed(() =>
		dayItems.value.filter((item) => !item.room || roomIndex.value[item.room] !== undefined),
	)
	const conflicts = computed(() => builder.conflicts(dayItems.value))
	const lanes = computed(() =>
		Object.assign(
			{},
			...rooms.value.map((room) =>
				lanesOf(dayItems.value.filter((item) => item.room === room.name)),
			),
		),
	)
	const countIn = (room: string) => dayItems.value.filter((item) => item.room === room).length
	return { builder, board, rooms, dayItems, roomIndex, visible, conflicts, lanes, countIn }
}
