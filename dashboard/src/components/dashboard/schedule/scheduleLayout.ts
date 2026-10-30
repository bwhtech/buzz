import type { ScheduleItem, ScheduleTalk } from "./scheduleTypes"

export const SNAP_MINUTES = 15
export const MIN_DURATION = 5
export const DEFAULT_START = 9 * 60
export const HOUR_HEIGHT = 112
export const TIMELINE_RATIO = 1.6
export const ROW_HEIGHT = 84
export const DURATIONS = [5, 10, 15, 20, 25, 30, 40, 45, 60, 75, 90, 120, 150, 180]
// Talk-like types come from the talks library; the rest are the blocks organizers drop in.
export const TALK_TYPES = new Set(["Talk", "Keynote", "Lightning", "Workshop", "Break"])

const pad = (value: number) => String(value).padStart(2, "0")

export const clock = (minutes: number) => `${pad(Math.floor(minutes / 60))}:${pad(minutes % 60)}`
export const hourLabel = (minutes: number) => `${pad(Math.floor(minutes / 60))}:00`
export const timeRange = (item: ScheduleItem) =>
	`${clock(item.start)} – ${clock(item.start + item.duration)}`
export const snap = (minutes: number) => Math.round(minutes / SNAP_MINUTES) * SNAP_MINUTES
export const snapDown = (minutes: number) => Math.floor(minutes / SNAP_MINUTES) * SNAP_MINUTES
export const clamp = (value: number, low: number, high: number) =>
	Math.max(low, Math.min(high, value))
export const talkMatches = (talk: ScheduleTalk, query: string) =>
	`${talk.title} ${talk.speakers.join(" ")}`.toLowerCase().includes(query)

export function durationLabel(minutes: number) {
	if (minutes < 60) return `${minutes} min`
	const rest = minutes % 60
	return `${Math.floor(minutes / 60)} hr${rest ? ` ${rest} min` : ""}`
}

export function speakerLine(names: string[]) {
	if (names.length < 2) return names[0] ?? ""
	if (names.length === 2) return `${names[0]} & ${names[1]}`
	return `${names[0]} and ${names.length - 1} others`
}

export interface DayRange {
	start: number
	end: number
}

export function hourMarks(range: DayRange) {
	const marks = []
	for (let minute = range.start; minute <= range.end; minute += 60) marks.push(minute)
	return marks
}

/** The usual conference day, stretched to hold every item. */
export function dayRange(items: ScheduleItem[]): DayRange {
	const starts = items.map((item) => item.start)
	const ends = items.map((item) => item.start + item.duration)
	return {
		start: Math.floor(Math.min(8 * 60, ...starts) / 60) * 60,
		end: Math.ceil(Math.max(19 * 60, ...ends) / 60) * 60,
	}
}

const overlaps = (a: ScheduleItem, b: ScheduleItem) =>
	a.start < b.start + b.duration && b.start < a.start + a.duration

export interface Lane {
	lane: number
	lanes: number
}

/** Overlapping items in one track sit side by side, one lane each. */
export function lanesOf(items: ScheduleItem[]): Record<string, Lane> {
	const sorted = items.toSorted((a, b) => a.start - b.start || b.duration - a.duration)
	const result: Record<string, Lane> = {}
	let cluster: string[] = []
	let ends: number[] = []
	let clusterEnd = -1
	const flush = () => {
		for (const key of cluster) result[key].lanes = ends.length || 1
		cluster = []
		ends = []
	}
	for (const item of sorted) {
		if (item.start >= clusterEnd) flush()
		let lane = ends.findIndex((end) => end <= item.start)
		if (lane < 0) lane = ends.push(0) - 1
		ends[lane] = item.start + item.duration
		result[item.key] = { lane, lanes: 1 }
		cluster.push(item.key)
		clusterEnd = Math.max(clusterEnd, ends[lane])
	}
	flush()
	return result
}

export interface ConflictContext {
	talks: Record<string, ScheduleTalk>
	trackTitle: (track: string | null) => string
}

const titleOf = (item: ScheduleItem, context: ConflictContext) =>
	(item.talk ? context.talks[item.talk]?.title : null) || item.title
const speakersOf = (item: ScheduleItem, context: ConflictContext) =>
	item.talk ? (context.talks[item.talk]?.speakers ?? []) : []

/** A message per item key: same-track overlaps, and one speaker in two tracks at once. */
export function conflictsOf(
	items: ScheduleItem[],
	context: ConflictContext,
): Record<string, string> {
	const result: Record<string, string> = {}
	const addConflict = (item: ScheduleItem, message: string) => (result[item.key] ??= message)
	items.forEach((a, index) => {
		for (const b of items.slice(index + 1)) {
			if (!overlaps(a, b)) continue
			if (a.track === b.track || !a.track || !b.track) {
				addConflict(a, `Overlaps “${titleOf(b, context)}”`)
				addConflict(b, `Overlaps “${titleOf(a, context)}”`)
				continue
			}
			const sharedSpeaker = speakersOf(a, context).find((name) =>
				speakersOf(b, context).includes(name),
			)
			if (!sharedSpeaker) continue
			addConflict(
				a,
				`${sharedSpeaker} is also speaking in ${context.trackTitle(b.track)} at this time`,
			)
			addConflict(
				b,
				`${sharedSpeaker} is also speaking in ${context.trackTitle(a.track)} at this time`,
			)
		}
	})
	return result
}

/** The first start at or after nine that clears the track, for a click-to-add. */
export function nextFreeStart(
	items: ScheduleItem[],
	track: string | null,
	duration: number,
	range: DayRange,
) {
	const busy = items
		.filter((item) => !track || item.track === track || !item.track)
		.toSorted((a, b) => a.start - b.start)
	let start = DEFAULT_START
	for (const item of busy) {
		if (start + duration <= item.start) break
		start = Math.max(start, item.start + item.duration)
	}
	return clamp(start, range.start, range.end - duration)
}
