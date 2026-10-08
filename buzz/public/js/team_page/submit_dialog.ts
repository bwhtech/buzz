// The Submit event dialog: lists the visitor's upcoming events and asks the community to list one.
interface EventOption {
	name: string
	title: string
	start_date: string
	team_name: string
}

interface CallResult<T> {
	data?: T
	errors?: { message?: string }[]
}

const METHOD = "/api/v2/method/buzz.api.communities"
const csrfToken = () =>
	(window as unknown as { frappe?: { csrf_token?: string } }).frappe?.csrf_token || ""

function call<T>(path: string, body?: Record<string, string>): Promise<T> {
	const init: RequestInit = body
		? {
				method: "POST",
				body: JSON.stringify(body),
				headers: { "Content-Type": "application/json", "X-Frappe-CSRF-Token": csrfToken() },
			}
		: {}
	return fetch(`${METHOD}.${path}`, init).then((response) =>
		response.json().then((result: CallResult<T>) => {
			if (!response.ok) throw new Error(result.errors?.[0]?.message || "Something went wrong")
			return result.data as T
		}),
	)
}

export class SubmitDialog {
	private community: string
	private form: HTMLFormElement
	private select: HTMLSelectElement
	private status: HTMLElement
	private confirm: HTMLButtonElement

	constructor(private dialog: HTMLDialogElement) {
		this.community = dialog.dataset.community || ""
		this.form = dialog.querySelector("[data-submit-form]")!
		this.select = dialog.querySelector("[data-submit-events]")!
		this.status = dialog.querySelector("[data-submit-status]")!
		this.confirm = dialog.querySelector("[data-submit-confirm]")!
		dialog.querySelector("[data-submit-cancel]")!.addEventListener("click", () => dialog.close())
		this.form.addEventListener("submit", (event) => {
			event.preventDefault()
			this.submit()
		})
	}

	open() {
		this.setStatus("")
		this.dialog.showModal()
		call<EventOption[]>(`get_submittable_events?community=${encodeURIComponent(this.community)}`)
			.then((events) => this.fill(events))
			.catch((error: Error) => this.setStatus(error.message, true))
	}

	private fill(events: EventOption[]) {
		this.select.replaceChildren(...events.map((event) => new Option(this.label(event), event.name)))
		this.showEmptyIfNone()
	}

	private showEmptyIfNone() {
		const isEmpty = !this.select.options.length
		if (isEmpty) this.select.append(new Option("You have no upcoming events to submit", ""))
		this.select.disabled = this.confirm.disabled = isEmpty
	}

	private label(event: EventOption): string {
		const date = new Date(`${event.start_date}T00:00`).toLocaleDateString(undefined, {
			day: "numeric",
			month: "short",
		})
		return `${event.title} · ${event.team_name} · ${date}`
	}

	private submit() {
		this.confirm.disabled = true
		call("submit_event", { event: this.select.value, community: this.community })
			.then(() => {
				this.select.selectedOptions[0]?.remove()
				this.setStatus("Submitted. You will get an email once it is reviewed.")
				this.showEmptyIfNone()
			})
			.catch((error: Error) => {
				this.confirm.disabled = false
				this.setStatus(error.message, true)
			})
	}

	private setStatus(text: string, failed = false) {
		this.status.textContent = text
		this.status.toggleAttribute("data-failed", failed)
	}
}
