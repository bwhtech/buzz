// Plain dayjs, not dayjsLocal: these are date-only values, and shifting them
// between timezones lands them on the day before.
import { dayjs, dayjsLocal } from "frappe-ui"

export function monthLabel(month: string): string {
	return dayjs(`${month}-01`).format("MMMM YYYY")
}

// frappe-ui's dayjs ships isToday but not the calendar plugin, so tomorrow is compared by hand.
export function dayLabel(date: string): string {
	const day = dayjs(date)
	if (day.isToday()) return "Today"
	if (day.isSame(dayjs().add(1, "day"), "day")) return "Tomorrow"
	return day.format("D MMM")
}

// A range crossing into another year names both years; "20 Nov – 1 Jul" reads as going backwards.
export function rangeLabel(start: string, end: string): string {
	if (dayjs(start).isSame(end, "year")) return `${dayLabel(start)} – ${dayLabel(end)}`
	return `${dayjs(start).format("D MMM YYYY")} – ${dayjs(end).format("D MMM YYYY")}`
}

export function weekday(date: string): string {
	return dayjs(date).format("dddd")
}

// Times arrive as a serialized timedelta ("9:00:00"), so the hour needs padding and the
// seconds dropping — slicing the raw string cuts a single-digit hour mid-segment.
export function timeLabel(time: string): string {
	const [hour, minute] = time.split(":")
	return `${hour.padStart(2, "0")}:${minute}`
}

/** Same serialized timedelta, rendered on a 12-hour clock: "9:30 AM". */
export function timeLabel12Hour(time: string): string {
	return dayjs(`2000-01-01 ${time}`).format("h:mm A")
}

/** A check-in's time, with its day when it was not today: "9:32 AM", "12 Nov, 9:32 AM". */
export function checkInTimeLabel(at: string): string {
	const time = dayjsLocal(at)
	return time.format(time.isToday() ? "h:mm A" : "D MMM, h:mm A")
}

// "just now", "3m ago", "4h ago", "2d ago", then the date: "Jun 24", with the year
// once it is not this year's.
export function editedAgo(timestamp: string, now: Date = new Date()): string {
	const then = dayjsLocal(timestamp)
	const minutes = dayjs(now).diff(then, "minute")
	if (minutes < 1) return "just now"
	if (minutes < 60) return `${minutes}m ago`
	const hours = Math.floor(minutes / 60)
	if (hours < 24) return `${hours}h ago`
	if (hours < 24 * 7) return `${Math.floor(hours / 24)}d ago`
	return then.format(then.isSame(dayjs(now), "year") ? "MMM D" : "MMM D, YYYY")
}
