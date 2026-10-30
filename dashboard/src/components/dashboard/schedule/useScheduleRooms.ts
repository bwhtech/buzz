import { useList } from "frappe-ui"
import { computed } from "vue"

import { ROOM_COLORS } from "./scheduleColors"
import type { ScheduleRoom } from "./scheduleTypes"

/** Rooms are Buzz Schedule Track rows; each change goes to the server at once. */
export function useScheduleRooms(scheduleName: () => string) {
	const list = useList<ScheduleRoom>({
		doctype: "Buzz Schedule Track",
		fields: ["name", "title", "color", "capacity", "sequence"],
		filters: () => ({ schedule: scheduleName() }),
		orderBy: "sequence asc, creation asc" as "sequence asc",
		limit: 50,
		immediate: false,
	})
	const rooms = computed(() => list.data ?? [])
	const find = (name: string | null) => rooms.value.find((room) => room.name === name)
	const titleOf = (name: string | null) => (name ? (find(name)?.title ?? "—") : "All rooms")
	const colorOf = (name: string | null) => {
		const index = rooms.value.findIndex((room) => room.name === name)
		return ROOM_COLORS[Math.max(index, 0) % ROOM_COLORS.length]
	}

	async function add(title: string) {
		const body = { title, schedule: scheduleName(), sequence: rooms.value.length }
		await list.insert.submit(body as unknown as Partial<ScheduleRoom>)
		await list.reload()
	}

	const rename = (name: string, title: string) => list.setValue.submit({ name, title })

	async function move(name: string, step: -1 | 1) {
		const order = rooms.value.map((room) => room.name)
		const from = order.indexOf(name)
		const to = from + step
		if (to < 0 || to >= order.length) return
		;[order[from], order[to]] = [order[to], order[from]]
		for (const [sequence, room] of order.entries()) {
			if (find(room)?.sequence !== sequence) await list.setValue.submit({ name: room, sequence })
		}
		await list.reload()
	}

	async function remove(name: string) {
		await list.delete.submit({ name })
		await list.reload()
	}

	return { rooms, find, titleOf, colorOf, add, rename, move, remove, reload: list.reload }
}
