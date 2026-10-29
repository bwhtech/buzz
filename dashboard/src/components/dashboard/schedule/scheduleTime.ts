import type { ScheduleItem } from "./scheduleTypes"

export const SNAP_MINUTES = 15
export const DEFAULT_DURATION_MINUTES = 30
const MINUTES_PER_DAY = 24 * 60

export function toMinutes(time: string): number {
	const [hours, minutes] = time.split(":").map(Number)
	return hours * 60 + minutes
}

const pad = (value: number) => String(value).padStart(2, "0")

export function toTime(minutes: number): string {
	const clamped = Math.max(0, Math.min(minutes, MINUTES_PER_DAY - 1))
	return `${pad(Math.floor(clamped / 60))}:${pad(clamped % 60)}:00`
}

export function startMinutes(item: ScheduleItem): number {
	return toMinutes(item.start_time)
}

export function endMinutes(item: ScheduleItem): number {
	return startMinutes(item) + Math.round(item.duration / 60)
}

export function snap(minutes: number): number {
	return Math.round(minutes / SNAP_MINUTES) * SNAP_MINUTES
}

export function hourLabel(minutes: number): string {
	return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:00`
}

export function clockLabel(time: string): string {
	return time.slice(0, 5)
}

export function durationLabel(minutes: number): string {
	if (minutes < 60) return `${minutes} min`
	const hours = Math.floor(minutes / 60)
	return minutes % 60 ? `${hours} h ${minutes % 60} min` : `${hours} h`
}

const overlaps = (first: ScheduleItem, second: ScheduleItem) =>
	startMinutes(first) < endMinutes(second) && startMinutes(second) < endMinutes(first)

export interface PlacedItem {
	item: ScheduleItem
	lane: number
	lanes: number
	conflict: boolean
}

/** Overlapping items share a track side by side, one lane each. */
export function placeInLanes(items: ScheduleItem[]): PlacedItem[] {
	const sorted = items.toSorted((a, b) => startMinutes(a) - startMinutes(b))
	const placed: PlacedItem[] = []
	let cluster: PlacedItem[] = []
	let clusterEnd = -1
	const closeCluster = () => {
		const lanes = Math.max(1, ...cluster.map((entry) => entry.lane + 1))
		for (const entry of cluster) {
			entry.lanes = lanes
			entry.conflict = cluster.length > 1
		}
		placed.push(...cluster)
		cluster = []
	}
	for (const item of sorted) {
		if (cluster.length && startMinutes(item) >= clusterEnd) closeCluster()
		const taken = new Set(
			cluster.filter((entry) => overlaps(entry.item, item)).map((entry) => entry.lane),
		)
		let lane = 0
		while (taken.has(lane)) lane++
		cluster.push({ item, lane, lanes: 1, conflict: false })
		clusterEnd = Math.max(clusterEnd, endMinutes(item))
	}
	if (cluster.length) closeCluster()
	return placed
}

/** Keys of the items that overlap another item in the same track, or any item when one spans all tracks. */
export function conflictingKeys(items: ScheduleItem[]): Set<string> {
	const keys = new Set<string>()
	items.forEach((first, index) => {
		for (const second of items.slice(index + 1)) {
			const sameTrack = first.track === second.track
			const spansAll = first.all_tracks || second.all_tracks
			const sameDay = first.date === second.date
			if (sameDay && (sameTrack || spansAll) && overlaps(first, second)) {
				keys.add(first.key).add(second.key)
			}
		}
	})
	return keys
}

/** The first free start in a track at or after the given minute, for a click-to-add. */
export function nextFreeStart(
	items: ScheduleItem[],
	track: string | null,
	fromMinutes: number,
	duration: number,
): number {
	const busy = items
		.filter((item) => item.all_tracks || item.track === track)
		.toSorted((a, b) => startMinutes(a) - startMinutes(b))
	let start = fromMinutes
	for (const item of busy) {
		if (endMinutes(item) <= start) continue
		if (startMinutes(item) >= start + duration) break
		start = endMinutes(item)
	}
	return start
}

const DEFAULT_RANGE = { start: 8 * 60, end: 18 * 60 }

/** The hours a day shows: the usual conference day, stretched to hold every item. */
export function dayRange(items: ScheduleItem[]): { start: number; end: number } {
	const starts = items.map(startMinutes)
	const ends = items.map(endMinutes)
	return {
		start: Math.floor(Math.min(DEFAULT_RANGE.start, ...starts) / 60) * 60,
		end: Math.ceil(Math.max(DEFAULT_RANGE.end, ...ends) / 60) * 60,
	}
}

const DEFAULT_MINUTES: Record<string, number> = { Break: 15, Workshop: 90 }

export const defaultMinutes = (type: string) => DEFAULT_MINUTES[type] ?? DEFAULT_DURATION_MINUTES
