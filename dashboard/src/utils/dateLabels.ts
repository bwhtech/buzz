// Plain dayjs, not dayjsLocal: these are date-only values, and shifting them
// between timezones lands them on the day before.
import { dayjs } from "frappe-ui"

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
