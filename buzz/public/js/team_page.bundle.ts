// A team page: Upcoming / Past tabs, and with events, the map, country chips and calendar.
import { MonthCalendar } from "./team_page/calendar"
import { TeamMap } from "./team_page/map"
import { readPageData } from "./team_page/page_data"
import { SubmitDialog } from "./team_page/submit_dialog"
import { scrollAndHighlight, showPanel, wireTabs } from "./team_page/timeline"

wireTabs()

const data = readPageData()
const mapElement = document.querySelector<HTMLElement>("[data-map]")
const map = data && mapElement ? new TeamMap(mapElement, data.upcoming) : null
const visitorTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
const visitorCountry = data?.time_zone_countries[visitorTimeZone] || ""
const countryChips = [...document.querySelectorAll<HTMLButtonElement>("[data-country-filter]")]
const nearbyButton = document.querySelector<HTMLButtonElement>('[data-zoom-to="nearby"]')
const worldButton = document.querySelector<HTMLButtonElement>('[data-zoom-to="world"]')

function hasVisibleEvents(scope: Element): boolean {
	return Boolean(scope.querySelector("[data-event-card]:not([hidden])"))
}

// Shows one country's events, or every event for "".
function filterByCountry(country: string) {
	for (const chip of countryChips) {
		chip.setAttribute("aria-pressed", String(chip.dataset.countryFilter === country))
	}
	nearbyButton?.setAttribute("aria-pressed", String(Boolean(country) && country === visitorCountry))
	worldButton?.setAttribute("aria-pressed", String(!country))
	for (const card of document.querySelectorAll<HTMLElement>("[data-event-card]")) {
		card.hidden = Boolean(country) && card.dataset.country !== country
	}
	for (const group of document.querySelectorAll<HTMLElement>("[data-day-group]")) {
		group.hidden = !hasVisibleEvents(group)
	}
	// A panel with no events at all already says so; this note is for one the filter emptied.
	for (const note of document.querySelectorAll<HTMLElement>("[data-filter-empty]")) {
		const panel = note.parentElement!
		note.hidden = !country || hasVisibleEvents(panel) || !panel.querySelector("[data-event-card]")
	}
	map?.filterByCountry(country)
}

function showDate(date: string) {
	const group = document.querySelector<HTMLElement>(`[data-day="${date}"]`)
	if (!group) return
	if (group.hidden) filterByCountry("")
	showPanel(group.closest<HTMLElement>("[data-panel]")?.dataset.panel || "upcoming")
	scrollAndHighlight(group)
}

for (const chip of countryChips) {
	chip.addEventListener("click", () => filterByCountry(chip.dataset.countryFilter || ""))
}
nearbyButton?.addEventListener("click", () => filterByCountry(visitorCountry))
worldButton?.addEventListener("click", () => filterByCountry(""))
if (nearbyButton) nearbyButton.hidden = !visitorCountry
for (const card of document.querySelectorAll<HTMLElement>("[data-event-card]")) {
	card.addEventListener("pointerenter", () => map?.highlightEvent(card.dataset.eventRoute || null))
	card.addEventListener("pointerleave", () => map?.highlightEvent(null))
}
const calendarElement = document.querySelector<HTMLElement>("[data-calendar]")
if (data && calendarElement) new MonthCalendar(calendarElement, data, showDate).render()
if (data && countryChips.length) filterByCountry(visitorCountry)

const submitDialogElement = document.querySelector<HTMLDialogElement>("#submit-dialog")
if (submitDialogElement) {
	const submitDialog = new SubmitDialog(submitDialogElement)
	document.querySelector("[data-open-submit]")?.addEventListener("click", () => submitDialog.open())
}
