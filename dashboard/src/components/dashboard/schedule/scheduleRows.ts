import type { ScheduleItem, ScheduleItemRow } from "./scheduleTypes"

const TALK_DOCTYPE = "Event Talk"
const pad = (value: number) => String(value).padStart(2, "0")

export const toMinutes = (time: string) => {
	const [hours, minutes] = time.split(":").map(Number)
	return hours * 60 + minutes
}

export const toTime = (minutes: number) =>
	`${pad(Math.floor(minutes / 60))}:${pad(minutes % 60)}:00`

export function newKey() {
	return Math.random().toString(36).slice(2, 10)
}

export function fromRow(row: ScheduleItemRow): ScheduleItem {
	const isTalk = row.reference_doctype === TALK_DOCTYPE && row.reference_document
	return {
		key: newKey(),
		date: row.date,
		room: row.all_tracks ? null : row.track,
		start: toMinutes(row.start_time),
		duration: Math.round(row.duration / 60),
		type: row.type,
		title: row.title ?? "",
		talk: isTalk ? String(row.reference_document) : null,
	}
}

export function toRow(item: ScheduleItem): ScheduleItemRow {
	return {
		date: item.date,
		type: item.type,
		title: item.title,
		reference_doctype: item.talk ? TALK_DOCTYPE : null,
		reference_document: item.talk,
		all_tracks: item.room ? 0 : 1,
		track: item.room,
		start_time: toTime(item.start),
		duration: item.duration * 60,
		end_time: toTime(item.start + item.duration),
	}
}
