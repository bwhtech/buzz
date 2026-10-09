const SECONDS_IN = { day: 86400, hour: 3600, minute: 60 }

/**
 * Time left as the dashboard's countdown pill words it: "14d 5h 55m", with the leading
 * empty units dropped. Under an hour, seconds join so the pill keeps visibly ticking.
 */
export function formatTimeLeft(milliseconds: number): string {
	const total = Math.max(0, Math.floor(milliseconds / 1000))
	const days = Math.floor(total / SECONDS_IN.day)
	const hours = Math.floor((total % SECONDS_IN.day) / SECONDS_IN.hour)
	const minutes = Math.floor((total % SECONDS_IN.hour) / SECONDS_IN.minute)
	const seconds = String(total % SECONDS_IN.minute).padStart(2, "0")
	if (days) return `${days}d ${hours}h ${minutes}m`
	if (hours) return `${hours}h ${minutes}m`
	return `${minutes}m ${seconds}s`
}
