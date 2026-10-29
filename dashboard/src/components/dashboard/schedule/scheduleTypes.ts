export interface ScheduleDay {
	date: string
	label: string
}

export interface ScheduleItem {
	// Client-only identity: rows have no name until the schedule is saved.
	key: string
	name?: string
	date: string
	type: string
	title: string
	reference_doctype?: string | null
	reference_document?: string | null
	all_tracks: 0 | 1
	track: string | null
	start_time: string
	duration: number
	end_time?: string
}

export interface ScheduleTrack {
	name: string
	title: string
	color: string | null
}

export interface ScheduleItemType {
	name: string
	title: string
	color: string | null
	icon: string | null
	is_standard: 0 | 1
}

export interface ScheduleDoc {
	name: string
	event: string
	is_published: 0 | 1
	days: string | ScheduleDay[] | null
	items: ScheduleItem[]
	modified: string
}

export interface ScheduleTalk {
	name: string
	title: string
	speakers: string
}

export type ScheduleView = "calendar" | "timeline"

// What a rail row carries when it is dragged onto the schedule.
export const DRAG_TYPE = "application/x-schedule"
