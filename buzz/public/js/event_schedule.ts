// Without scripting every day is listed in full; this adds the day switcher, the room filter
// and the search on top of that same markup.
export class EventSchedule extends HTMLElement {
	private day = ""
	private room = ""
	private query = ""

	connectedCallback() {
		this.day = this.querySelector<HTMLElement>(".schedule-day")?.dataset.day ?? ""
		this.addEventListener("click", (event) => this.handleClick(event.target as HTMLElement))
		this.addEventListener("input", (event) => this.handleInput(event.target as HTMLInputElement))
		this.querySelectorAll("[data-controls]").forEach((controls) =>
			controls.removeAttribute("hidden"),
		)
		this.dataset.ready = ""
		this.render()
	}

	private handleClick(target: HTMLElement) {
		const dayButton = target.closest<HTMLElement>(".schedule-day-button")
		const roomButton = target.closest<HTMLElement>(".schedule-room-button")
		if (dayButton) this.day = dayButton.dataset.day ?? ""
		else if (roomButton) this.room = roomButton.dataset.room ?? ""
		else if (target.closest("[data-clear-filters]")) this.clearFilters()
		else return
		this.render()
	}

	private handleInput(input: HTMLInputElement) {
		if (!input.matches(".schedule-search")) return
		this.query = input.value.trim().toLowerCase()
		this.render()
	}

	private clearFilters() {
		this.room = ""
		this.query = ""
		const search = this.querySelector<HTMLInputElement>(".schedule-search")
		if (search) search.value = ""
	}

	private render() {
		this.toggleAttribute("data-filtered", Boolean(this.room || this.query))
		this.markPressed(".schedule-day-button", "day", this.day)
		this.markPressed(".schedule-room-button", "room", this.room)
		this.querySelectorAll<HTMLElement>(".schedule-day").forEach((day) => {
			day.hidden = day.dataset.day !== this.day
		})
		this.querySelectorAll<HTMLElement>(".schedule-item").forEach((item) => {
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
		const inRoom = !this.room || !item.dataset.room || item.dataset.room === this.room
		const inSearch = !this.query || (item.textContent ?? "").toLowerCase().includes(this.query)
		return inRoom && inSearch
	}

	private showEmptyState() {
		const visible = this.querySelector(".schedule-day:not([hidden]) .schedule-item:not([hidden])")
		const empty = this.querySelector<HTMLElement>(".schedule-empty")
		if (empty) empty.hidden = Boolean(visible)
	}
}
