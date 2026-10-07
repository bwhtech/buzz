export interface EventCard {
	route: string
	date: string
	title: string
	url: string
	time: string
	city: string | null
	country: string | null
	latitude: number | null
	longitude: number | null
}

export interface PageData {
	upcoming: EventCard[]
	past: EventCard[]
	today: string
	time_zone_countries: Record<string, string>
}

export const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)")

const dayFormat = new Intl.DateTimeFormat(undefined, {
	weekday: "short",
	month: "short",
	day: "numeric",
})

export function formatDay(date: string): string {
	return dayFormat.format(new Date(`${date}T00:00`))
}

export function readPageData(): PageData | null {
	const script = document.getElementById("team-page-data")
	return script ? JSON.parse(script.textContent || "null") : null
}
