const MINUTES_PER_DAY = 24 * 60
const pad = (value: number) => String(value).padStart(2, "0")

// A time that lands on another day than its schedule day is marked with that weekday.
function clock(minutes: number, date: string) {
	const days = Math.floor(minutes / MINUTES_PER_DAY)
	const wrapped = minutes - days * MINUTES_PER_DAY
	const time = `${pad(Math.floor(wrapped / 60))}:${pad(wrapped % 60)}`
	if (!days) return time
	const day = new Date(`${date}T12:00:00Z`)
	day.setUTCDate(day.getUTCDate() + days)
	const weekday = new Intl.DateTimeFormat(undefined, { weekday: "short", timeZone: "UTC" })
	return `${time} ${weekday.format(day)}`
}

// Minutes a time zone is ahead of UTC at that instant.
function zoneOffset(timeZone: string, instant: Date) {
	const parts = Object.fromEntries(
		new Intl.DateTimeFormat("en-US", {
			timeZone,
			hourCycle: "h23",
			year: "numeric",
			month: "numeric",
			day: "numeric",
			hour: "numeric",
			minute: "numeric",
		})
			.formatToParts(instant)
			.map((part) => [part.type, Number(part.value)]),
	)
	const wall = Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute)
	return Math.round((wall - instant.getTime()) / 60000)
}

// A speaker photo that fails to load shows the speaker's initial instead.
function showInitial(image: HTMLImageElement) {
	const initial = document.createElement("span")
	initial.className = image.className
	initial.textContent = image.dataset.initial ?? ""
	initial.setAttribute("aria-hidden", "true")
	image.replaceWith(initial)
}

function localZoneName() {
	const zone = Intl.DateTimeFormat().resolvedOptions().timeZone
	const short = new Intl.DateTimeFormat("en-US", { timeZoneName: "short" })
		.formatToParts(new Date())
		.find((part) => part.type === "timeZoneName")?.value
	return short && short !== zone ? `${zone} (${short})` : zone
}

// Without scripting every day is listed in full; this adds the day switcher, the track filter,
// the search and the list or grid layout on top of that same markup.
export class EventSchedule extends HTMLElement {
	private day = ""
	private track = ""
	private query = ""
	private layout = "list"
	private zone = "event"
	// Minutes to add to each day's event times to show them in the visitor's time zone.
	private shifts = new Map<string, number>()

	connectedCallback() {
		this.day = this.querySelector<HTMLElement>(".schedule-day")?.dataset.day ?? ""
		this.layout =
			new URLSearchParams(window.location.search).get("layout") === "grid" ? "grid" : "list"
		this.addEventListener("click", (event) => this.handleClick(event.target as HTMLElement))
		this.addEventListener("input", (event) => this.handleInput(event.target as HTMLInputElement))
		this.querySelectorAll("[data-controls]").forEach((controls) =>
			controls.removeAttribute("hidden"),
		)
		this.setUpTimeZones()
		this.replaceBrokenAvatars()
		this.addEventListener("scroll", () => this.markScrollableRows(), true)
		window.addEventListener("resize", () => this.markScrollableRows())
		this.dataset.ready = ""
		this.render()
	}

	private handleClick(target: HTMLElement) {
		const dayButton = target.closest<HTMLElement>(".schedule-day-button")
		const trackButton = target.closest<HTMLElement>(".schedule-track-button")
		const layoutButton = target.closest<HTMLElement>(".schedule-layout-button")
		const zoneButton = target.closest<HTMLElement>(".schedule-zone-button")
		if (dayButton) this.day = dayButton.dataset.day ?? ""
		else if (trackButton) this.track = trackButton.dataset.track ?? ""
		else if (layoutButton) this.setLayout(layoutButton.dataset.layout ?? "list")
		else if (zoneButton) this.zone = zoneButton.dataset.zone ?? "event"
		else if (target.closest("[data-clear-filters]")) this.clearFilters()
		else if (target.closest("[data-open-detail]")) return this.openDetail(target)
		else if (target.matches(".schedule-dialog")) return this.closeDetail()
		else return
		this.render()
	}

	private replaceBrokenAvatars() {
		this.querySelectorAll<HTMLImageElement>("img[data-initial]").forEach((image) => {
			if (image.complete && !image.naturalWidth) showInitial(image)
			else image.addEventListener("error", () => showInitial(image), { once: true })
		})
	}

	// Rows of buttons that scroll sideways fade out on the right while more is hidden there.
	private markScrollableRows() {
		this.querySelectorAll<HTMLElement>(".schedule-days, .schedule-segments").forEach((row) => {
			const hidden = row.scrollWidth - row.clientWidth - row.scrollLeft
			row.toggleAttribute("data-more-right", hidden > 1)
		})
	}

	private setUpTimeZones() {
		const timeZone = this.dataset.timeZone
		if (!timeZone) return
		this.querySelectorAll<HTMLElement>(".schedule-day").forEach((day) => {
			const noon = new Date(`${day.dataset.day}T12:00:00Z`)
			this.shifts.set(day.dataset.day ?? "", -noon.getTimezoneOffset() - zoneOffset(timeZone, noon))
		})
		if (![...this.shifts.values()].some(Boolean)) return
		const note = this.querySelector<HTMLElement>("[data-local-note]")
		if (note) note.textContent = (this.dataset.localNote ?? "").replace("{0}", localZoneName())
		this.querySelector<HTMLElement>(".schedule-zones")?.removeAttribute("hidden")
	}

	private renderTimes() {
		const local = this.zone === "local"
		this.querySelector<HTMLElement>("[data-event-note]")?.toggleAttribute("hidden", local)
		this.querySelector<HTMLElement>("[data-local-note]")?.toggleAttribute("hidden", !local)
		this.querySelectorAll<HTMLElement>(".schedule-day").forEach((day) => {
			const date = day.dataset.day ?? ""
			const shift = local ? (this.shifts.get(date) ?? 0) : 0
			day.querySelectorAll<HTMLElement>("time[data-minutes]").forEach((time) => {
				time.textContent = clock(Number(time.dataset.minutes) + shift, date)
			})
		})
	}

	private setLayout(layout: string) {
		this.layout = layout
		const url = new URL(window.location.href)
		if (layout === "grid") url.searchParams.set("layout", "grid")
		else url.searchParams.delete("layout")
		window.history.replaceState(null, "", url)
	}

	private openDetail(target: HTMLElement) {
		const detail = target.closest(".schedule-block")?.querySelector(".schedule-block-detail")
		const dialog = this.querySelector<HTMLDialogElement>(".schedule-dialog")
		const body = dialog?.querySelector(".schedule-dialog-body")
		if (!detail || !dialog || !body) return
		body.innerHTML = detail.innerHTML
		dialog.showModal()
	}

	private closeDetail() {
		this.querySelector<HTMLDialogElement>(".schedule-dialog")?.close()
	}

	private handleInput(input: HTMLInputElement) {
		if (!input.matches(".schedule-search")) return
		this.query = input.value.trim().toLowerCase()
		this.render()
	}

	private clearFilters() {
		this.track = ""
		this.query = ""
		const search = this.querySelector<HTMLInputElement>(".schedule-search")
		if (search) search.value = ""
	}

	private render() {
		this.toggleAttribute("data-filtered", Boolean(this.track || this.query))
		this.markPressed(".schedule-day-button", "day", this.day)
		this.markPressed(".schedule-track-button", "track", this.track)
		this.markPressed(".schedule-layout-button", "layout", this.layout)
		this.markPressed(".schedule-zone-button", "zone", this.zone)
		this.renderTimes()
		this.markScrollableRows()
		this.dataset.layout = this.layout
		this.querySelectorAll<HTMLElement>(".schedule-grid-title, .schedule-grid-column").forEach(
			(column) => {
				column.hidden = Boolean(this.track) && column.dataset.track !== this.track
			},
		)
		this.querySelectorAll<HTMLElement>(".schedule-day").forEach((day) => {
			day.hidden = day.dataset.day !== this.day
		})
		this.querySelectorAll<HTMLElement>(".schedule-item, .schedule-block").forEach((item) => {
			item.hidden = !this.isShown(item)
		})
		this.querySelectorAll<HTMLElement>(".schedule-slot").forEach((slot) => {
			slot.hidden = !slot.querySelector(".schedule-item:not([hidden])")
		})
		this.showEmptyState()
	}

	private markPressed(selector: string, key: string, value: string) {
		this.querySelectorAll<HTMLElement>(selector).forEach((button) => {
			button.setAttribute("aria-pressed", String(button.dataset[key] === value))
		})
	}

	private isShown(item: HTMLElement): boolean {
		const inTrack = !this.track || !item.dataset.track || item.dataset.track === this.track
		const inSearch = !this.query || (item.textContent ?? "").toLowerCase().includes(this.query)
		return inTrack && inSearch
	}

	private showEmptyState() {
		const visible = this.querySelector(
			".schedule-day:not([hidden]) :is(.schedule-item, .schedule-block):not([hidden])",
		)
		const empty = this.querySelector<HTMLElement>(".schedule-empty")
		if (empty) empty.hidden = Boolean(visible)
	}
}
