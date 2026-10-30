import { useList } from "frappe-ui"
import { computed } from "vue"

import { TRACK_COLORS } from "./scheduleColors"
import type { ScheduleTrack } from "./scheduleTypes"

const FIELDS = ["name", "title", "color", "capacity", "sequence", "is_standard"] as const

/**
 * Tracks are Buzz Schedule Track rows; each change goes to the server at once. The standard
 * track is shared, so it shows only while the schedule has no track of its own or still uses it.
 */
export function useScheduleTracks(scheduleName: () => string, isUsed: (track: string) => boolean) {
	const list = useList<ScheduleTrack>({
		doctype: "Buzz Schedule Track",
		fields: [...FIELDS],
		filters: () => ({ schedule: scheduleName() }),
		orderBy: "sequence asc, creation asc" as "sequence asc",
		limit: 50,
		immediate: false,
	})
	const standard = useList<ScheduleTrack>({
		doctype: "Buzz Schedule Track",
		fields: [...FIELDS],
		filters: { is_standard: 1 },
		orderBy: "sequence asc",
		limit: 10,
	})
	const scheduleTracks = computed(() => list.data ?? [])
	const tracks = computed(() => {
		const sharedTracks = (standard.data ?? []).filter(
			(track) => !scheduleTracks.value.length || isUsed(track.name),
		)
		return [...sharedTracks, ...scheduleTracks.value].toSorted((a, b) => a.sequence - b.sequence)
	})
	const find = (name: string | null) => tracks.value.find((track) => track.name === name)
	const titleOf = (name: string | null) => (name ? (find(name)?.title ?? "—") : "All tracks")
	const colorOf = (name: string | null) => {
		const index = tracks.value.findIndex((track) => track.name === name)
		return TRACK_COLORS[Math.max(index, 0) % TRACK_COLORS.length]
	}

	async function add(title: string) {
		const body = { title, schedule: scheduleName(), sequence: tracks.value.length }
		await list.insert.submit(body as unknown as Partial<ScheduleTrack>)
		await list.reload()
	}

	const rename = (name: string, title: string) => list.setValue.submit({ name, title })

	async function move(name: string, step: -1 | 1) {
		const order = tracks.value.map((track) => track.name)
		const from = order.indexOf(name)
		const to = from + step
		if (to < 0 || to >= order.length) return
		;[order[from], order[to]] = [order[to], order[from]]
		for (const [sequence, track] of order.entries()) {
			if (find(track)?.sequence !== sequence) await list.setValue.submit({ name: track, sequence })
		}
		await list.reload()
	}

	async function remove(name: string) {
		await list.delete.submit({ name })
		await list.reload()
	}

	return { tracks, find, titleOf, colorOf, add, rename, move, remove, reload: list.reload }
}
