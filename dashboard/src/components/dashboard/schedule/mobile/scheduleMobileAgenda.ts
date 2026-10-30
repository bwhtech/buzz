import { clock, durationLabel } from "../scheduleLayout"
import type { ScheduleItem } from "../scheduleTypes"

export const MIN_GAP = 15

export interface AgendaGroup {
	kind: "group"
	start: number
	items: ScheduleItem[]
}

export interface AgendaGap {
	kind: "gap"
	start: number
	label: string
}

export type AgendaEntry = AgendaGroup | AgendaGap

const gapBetween = (from: number, to: number): AgendaGap => ({
	kind: "gap",
	start: from,
	label: `${durationLabel(to - from)} free · ${clock(from)}–${clock(to)}`,
})

/** Items grouped by start time, with a gap entry wherever the day sits idle. */
export function buildAgenda(
	items: ScheduleItem[],
	trackOrder: Record<string, number>,
	dayEnd: number,
): AgendaEntry[] {
	const order = (item: ScheduleItem) => trackOrder[item.track ?? ""] ?? -1
	const sorted = items.toSorted((a, b) => a.start - b.start || order(a) - order(b))
	const entries: AgendaEntry[] = []
	let current = null as AgendaGroup | null
	let latestEnd: number | null = null
	for (const item of sorted) {
		if (current?.start !== item.start) {
			if (latestEnd !== null && item.start - latestEnd >= MIN_GAP)
				entries.push(gapBetween(latestEnd, item.start))
			current = { kind: "group", start: item.start, items: [] }
			entries.push(current)
		}
		current!.items.push(item)
		latestEnd = Math.max(latestEnd ?? 0, item.start + item.duration)
	}
	if (latestEnd !== null && latestEnd < dayEnd)
		entries.push({ kind: "gap", start: latestEnd, label: `Add after ${clock(latestEnd)}` })
	return entries
}
