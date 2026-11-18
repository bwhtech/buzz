import { dayjsLocal } from "frappe-ui"

import { normalizedTime } from "@/utils/eventDates"

const pad = (value: number) => String(value).padStart(2, "0")

export function minutesOf(time: string): number {
	if (!time) return 0
	const [hour = "0", minute = "0"] = normalizedTime(time).split(":")
	return Number(hour) * 60 + Number(minute)
}

export const timeOf = (minutes: number) =>
	`${pad(Math.floor(minutes / 60))}:${pad(minutes % 60)}:00`

export const TIME_SLOTS = Array.from({ length: 48 }, (_, index) => timeOf(index * 30))

export function formatTime(time: string): string {
	const minutes = minutesOf(time)
	const hour = Math.floor(minutes / 60)
	return `${hour % 12 || 12}:${pad(minutes % 60)} ${hour < 12 ? "AM" : "PM"}`
}

/** Reads what people type: "7", "7pm", "19:30", "730p". Empty when it cannot. */
export function parseTime(text: string): string {
	const match = text
		.trim()
		.toLowerCase()
		.match(/^(\d{1,2})(?::?(\d{2}))?\s*(a|p|am|pm)?$/)
	if (!match) return ""
	let hour = Number(match[1])
	const minute = Number(match[2] ?? 0)
	const meridiem = match[3]?.[0]
	if (meridiem === "p" && hour < 12) hour += 12
	if (meridiem === "a" && hour === 12) hour = 0
	return hour < 24 && minute < 60 ? timeOf(hour * 60 + minute) : ""
}

export function formatDuration(minutes: number): string {
	if (minutes <= 0) return ""
	const hours = Math.floor(minutes / 60)
	const rest = minutes % 60
	if (!hours) return `${rest}m`
	return rest ? `${hours}h ${rest}m` : `${hours}h`
}

export const formatDateLabel = (date: string) => dayjsLocal(date).format("ddd, D MMM")

export const today = () => dayjsLocal().format("YYYY-MM-DD")

export interface ScheduleDraft {
	startDate: string
	startTime: string
	endDate: string
	endTime: string
	timeZone: string
}

/** Minutes from start to end, across days. */
export function scheduleLength(schedule: ScheduleDraft): number {
	const days = dayjsLocal(schedule.endDate).diff(dayjsLocal(schedule.startDate), "day")
	return days * 24 * 60 + minutesOf(schedule.endTime) - minutesOf(schedule.startTime)
}
