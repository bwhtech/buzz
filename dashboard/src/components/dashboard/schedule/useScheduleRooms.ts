import { useList } from "frappe-ui"
import { computed } from "vue"

import { ROOM_COLORS } from "./scheduleColors"
import type { ScheduleRoom } from "./scheduleTypes"

const FIELDS = ["name", "title", "color", "capacity", "sequence", "is_standard"] as const

/**
 * Rooms are Buzz Schedule Track rows; each change goes to the server at once. The standard
 * track is shared, so it shows only while the schedule has no track of its own or still uses it.
 */
export function useScheduleRooms(scheduleName: () => string, isUsed: (room: string) => boolean) {
	const list = useList<ScheduleRoom>({
		doctype: "Buzz Schedule Track",
		fields: [...FIELDS],
		filters: () => ({ schedule: scheduleName() }),
		orderBy: "sequence asc, creation asc" as "sequence asc",
		limit: 50,
		immediate: false,
	})
	const standard = useList<ScheduleRoom>({
		doctype: "Buzz Schedule Track",
		fields: [...FIELDS],
		filters: { is_standard: 1 },
		orderBy: "sequence asc",
		limit: 10,
	})
	const own = computed(() => list.data ?? [])
	const rooms = computed(() => {
		const shared = (standard.data ?? []).filter((room) => !own.value.length || isUsed(room.name))
		return [...shared, ...own.value].toSorted((a, b) => a.sequence - b.sequence)
	})
	const find = (name: string | null) => rooms.value.find((room) => room.name === name)
	const titleOf = (name: string | null) => (name ? (find(name)?.title ?? "—") : "All tracks")
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
