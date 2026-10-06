import { formatDay, type PageData } from "./page_data"

// 1 January 2023 was a Sunday, the first column.
const WEEK = Array.from({ length: 7 }, (_, day) => new Date(2023, 0, 1 + day))
const weekdayFormat = new Intl.DateTimeFormat(undefined, { weekday: "narrow" })
const monthFormat = new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" })

function pad(value: number): string {
	return String(value).padStart(2, "0")
}

function formatIsoDate(date: Date): string {
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

/** A month grid with a dot on each day that has an event; a dotted day jumps to its group. */
export class MonthCalendar {
	private month: Date
	private datesWithEvents: Set<string>

	constructor(
		private root: HTMLElement,
		private data: PageData,
		private onSelectDate: (date: string) => void,
	) {
		const today = new Date(`${data.today}T00:00`)
		this.month = new Date(today.getFullYear(), today.getMonth(), 1)
		this.datesWithEvents = new Set([...data.upcoming, ...data.past].map((event) => event.date))
		for (const button of root.querySelectorAll<HTMLButtonElement>("[data-calendar-step]")) {
			button.addEventListener("click", () => this.changeMonth(Number(button.dataset.calendarStep)))
		}
	}

	private changeMonth(months: number) {
		this.month = new Date(this.month.getFullYear(), this.month.getMonth() + months, 1)
		this.render()
	}

	render() {
		this.root.querySelector("[data-calendar-title]")!.textContent = monthFormat.format(this.month)
		const grid = this.root.querySelector<HTMLElement>("[data-calendar-grid]")!
		grid.replaceChildren(
			...WEEK.map((day) => this.weekday(day)),
			...this.emptyCells(),
			...this.dayCells(),
		)
	}

	private weekday(day: Date): HTMLElement {
		const cell = document.createElement("span")
		cell.className = "calendar-weekday"
		cell.textContent = weekdayFormat.format(day)
		return cell
	}

	private emptyCells(): HTMLElement[] {
		return Array.from({ length: this.month.getDay() }, () => document.createElement("span"))
	}

	private dayCells(): HTMLElement[] {
		const count = new Date(this.month.getFullYear(), this.month.getMonth() + 1, 0).getDate()
		return Array.from({ length: count }, (_, index) => this.dayCell(index + 1))
	}

	private dayCell(number: number): HTMLElement {
		const date = formatIsoDate(new Date(this.month.getFullYear(), this.month.getMonth(), number))
		const hasEvents = this.datesWithEvents.has(date)
		const cell = document.createElement(hasEvents ? "button" : "span")
		cell.className = "calendar-day"
		cell.textContent = String(number)
		cell.toggleAttribute("data-today", date === this.data.today)
		cell.toggleAttribute("data-past", date < this.data.today)
		if (hasEvents) this.addDateButton(cell as HTMLButtonElement, date)
		return cell
	}

	private addDateButton(button: HTMLButtonElement, date: string) {
		button.type = "button"
		button.setAttribute("aria-label", formatDay(date))
		button.append(Object.assign(document.createElement("span"), { className: "calendar-dot" }))
		button.addEventListener("click", () => this.onSelectDate(date))
	}
}
