export interface ScheduleDay {
	date: string
	label: string
}

/** One slot on the schedule. Times are minutes since midnight; a null room spans every room. */
export interface ScheduleItem {
	key: string
	date: string
	room: string | null
	start: number
	duration: number
	type: string
	title: string
	talk: string | null
}

export interface ScheduleRoom {
	name: string
	title: string
	color: string | null
	capacity: number | null
	sequence: number
}

export interface ScheduleItemType {
	name: string
	title: string
	color: string | null
	icon: string | null
	default_duration: number
	spans_all_tracks: 0 | 1
	is_standard: 0 | 1
}

export interface ScheduleTalk {
	name: string
	title: string
	speakers: string[]
}

export interface ScheduleItemRow {
	name?: string
	date: string
	type: string
	title: string | null
	reference_doctype: string | null
	reference_document: string | null
	all_tracks: 0 | 1
	track: string | null
	start_time: string
	duration: number
	end_time?: string
}

export interface ScheduleDoc {
	name: string
	event: string
	is_published: 0 | 1
	days: string | ScheduleDay[] | null
	items: ScheduleItemRow[]
	modified: string
}

export type ScheduleView = "calendar" | "timeline"

/** What a library row or a block carries while it is dragged. */
export interface DragPayload {
	kind: "item" | "talk" | "type"
	id: string
	duration: number
	span: boolean
	grabX: number
	grabY: number
}
