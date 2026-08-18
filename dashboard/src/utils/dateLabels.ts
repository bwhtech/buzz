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
