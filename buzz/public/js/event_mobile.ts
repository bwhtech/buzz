// The event page's phone layout: bottom sheets, the bottom bar, read more on a long About,
// and the share and calendar actions.

const PHONE = "(max-width: 720px)"
const LONG_ABOUT_HEIGHT = 480
const SHEET_CLOSE_MS = 220

interface IcsFields {
	title: string
	start: string
	end: string
	location: string
	url: string
}

class EventSheet {
	private title: HTMLElement
	private body: HTMLElement

	constructor(private dialog: HTMLDialogElement) {
		this.title = dialog.querySelector(".event-sheet-title") as HTMLElement
		this.body = dialog.querySelector(".event-sheet-body") as HTMLElement
		dialog.addEventListener("cancel", (event) => {
			event.preventDefault()
			this.close()
		})
		dialog.addEventListener("click", (event) => {
			if (event.target === dialog) this.close()
		})
	}

	open(name: string) {
		const template = document.querySelector<HTMLTemplateElement>(`template[data-sheet="${name}"]`)
		if (!template) return
		this.title.textContent = template.dataset.title || ""
		this.body.replaceChildren(template.content.cloneNode(true))
		if (!this.dialog.open) this.dialog.showModal()
		// Two frames, so the closed position paints before the slide starts
		requestAnimationFrame(() =>
			requestAnimationFrame(() => this.dialog.setAttribute("data-open", "")),
		)
	}

	close() {
		this.dialog.removeAttribute("data-open")
		setTimeout(() => {
			if (!this.dialog.hasAttribute("data-open")) this.dialog.close()
		}, SHEET_CLOSE_MS)
	}
}

// Shows the bar once the ticket cards have scrolled up past the site header.
function watchDock(dock: HTMLElement, cards: HTMLElement) {
	const header = document.querySelector<HTMLElement>(".buzz-navbar")
	const top = header ? header.offsetHeight : 0
	const observer = new IntersectionObserver(
		([entry]) => {
			const scrolledPast = !entry.isIntersecting && entry.boundingClientRect.top < top
			dock.toggleAttribute("data-shown", scrolledPast)
		},
		{ rootMargin: `-${top}px 0px 0px 0px` },
	)
	observer.observe(cards)
}

class AboutReadMore {
	private label: HTMLElement
	private closedLabel: string

	constructor(
		private section: HTMLElement,
		private button: HTMLButtonElement,
	) {
		this.label = button.querySelector("span") as HTMLElement
		this.closedLabel = this.label.textContent || ""
		button.addEventListener("click", () => this.toggle())
		const phone = matchMedia(PHONE)
		phone.addEventListener("change", () => this.measure())
	}

	measure() {
		const prose = this.section.querySelector(".prose") as HTMLElement
		const long = matchMedia(PHONE).matches && prose.scrollHeight > LONG_ABOUT_HEIGHT
		this.section.toggleAttribute("data-long", long)
		this.button.hidden = !long
	}

	toggle() {
		const opening = !this.section.hasAttribute("data-open")
		this.section.toggleAttribute("data-open", opening)
		this.button.setAttribute("aria-expanded", String(opening))
		this.label.textContent = opening ? this.button.dataset.openLabel || "" : this.closedLabel
		if (!opening) this.section.scrollIntoView({ block: "start", behavior: "smooth" })
	}
}

class EventToast {
	private timer = 0

	constructor(private element: HTMLElement) {}

	show(message: string) {
		this.element.textContent = message
		this.element.setAttribute("data-shown", "")
		clearTimeout(this.timer)
		this.timer = window.setTimeout(() => this.element.removeAttribute("data-shown"), 1800)
	}
}

function escapeIcsText(value: string): string {
	return value
		.replace(/\\/g, "\\\\")
		.replace(/;/g, "\\;")
		.replace(/,/g, "\\,")
		.replace(/\n/g, "\\n")
}

function downloadIcs(fields: IcsFields) {
	const lines = [
		"BEGIN:VCALENDAR",
		"VERSION:2.0",
		"PRODID:-//Buzz Events//EN",
		"BEGIN:VEVENT",
		`UID:${fields.start}-${fields.url}`,
		`DTSTAMP:${fields.start}`,
		`DTSTART:${fields.start}`,
		`DTEND:${fields.end}`,
		`SUMMARY:${escapeIcsText(fields.title)}`,
		`LOCATION:${escapeIcsText(fields.location)}`,
		`URL:${fields.url}`,
		"END:VEVENT",
		"END:VCALENDAR",
	]
	const file = new Blob([lines.join("\r\n")], { type: "text/calendar" })
	const link = Object.assign(document.createElement("a"), {
		href: URL.createObjectURL(file),
		download: "event.ics",
	})
	link.click()
	setTimeout(() => URL.revokeObjectURL(link.href), 1000)
}

function readIcsFields(): IcsFields | null {
	const script = document.querySelector("[data-calendar-ics]")
	return script ? (JSON.parse(script.textContent || "null") as IcsFields) : null
}

export function mountEventMobile() {
	const dialog = document.querySelector<HTMLDialogElement>("[data-event-sheet]")
	if (!dialog) return
	const sheet = new EventSheet(dialog)
	const toast = new EventToast(document.querySelector(".event-toast") as HTMLElement)
	const dock = document.querySelector<HTMLElement>("[data-event-dock]")
	const cards = document.querySelector<HTMLElement>(".side-cards")
	if (dock && cards) watchDock(dock, cards)
	const readMore = document.querySelector<HTMLButtonElement>("[data-read-more]")
	if (readMore) {
		const about = new AboutReadMore(readMore.closest(".section") as HTMLElement, readMore)
		about.measure()
	}

	const copyLink = (button: HTMLElement) =>
		navigator.clipboard
			.writeText(location.href)
			.then(() => toast.show(button.dataset.doneLabel || ""))
	const actions: Record<string, (button: HTMLElement) => void> = {
		"close-sheet": () => sheet.close(),
		share: (button) => {
			if (!navigator.share) return void copyLink(button)
			navigator.share({ title: document.title, url: location.href }).catch(() => {})
		},
		"copy-link": (button) => void copyLink(button),
		ics: () => {
			const fields = readIcsFields()
			if (fields) downloadIcs(fields)
		},
	}

	document.addEventListener("click", (event) => {
		const target = event.target as HTMLElement
		const action = target.closest<HTMLElement>("[data-action]")
		if (action && action.dataset.action && action.dataset.action in actions) {
			return actions[action.dataset.action](action)
		}
		const opener = target.closest<HTMLElement>("[data-sheet-open]")
		if (opener) {
			event.preventDefault()
			sheet.open(opener.dataset.sheetOpen || "")
		}
	})
}
