// "Submit event" on a community page: a native dialog listing the visitor's own events.
const API = "/api/v2/method/buzz.api.communities"

interface EventOption {
	name: string
	title: string
	team_name: string
}

declare const frappe: { csrf_token: string }

function callApi<T>(method: string, init?: RequestInit): Promise<T> {
	return fetch(`${API}.${method}`, init).then((response) =>
		response.json().then((body) => {
			if (!response.ok) throw new Error(body.errors?.[0]?.message || response.statusText)
			return body.data as T
		}),
	)
}

export class SubmitDialog {
	private form: HTMLFormElement
	private select: HTMLSelectElement
	private error: HTMLElement

	constructor(private dialog: HTMLDialogElement) {
		this.form = dialog.querySelector("[data-submit-form]")!
		this.select = this.form.querySelector("select")!
		this.error = this.form.querySelector("[data-submit-error]")!
		this.form.addEventListener("submit", (event) => {
			event.preventDefault()
			this.submit()
		})
		for (const button of dialog.querySelectorAll("[data-close-dialog]")) {
			button.addEventListener("click", () => dialog.close())
		}
		dialog.addEventListener("close", () => this.reset())
	}

	open() {
		this.dialog.showModal()
		const community = encodeURIComponent(this.dialog.dataset.community || "")
		callApi<EventOption[]>(`get_submittable_events?community=${community}`)
			.then((events) => this.showEvents(events))
			.catch((error: Error) => this.showError(error.message))
	}

	private showEvents(events: EventOption[]) {
		this.select.replaceChildren(
			...events.map((event) => new Option(`${event.title} · ${event.team_name}`, event.name)),
		)
		this.toggle("[data-submit-choice]", events.length > 0)
		this.toggle("[data-submit-empty]", events.length === 0)
		this.form.querySelector<HTMLButtonElement>("[data-submit-button]")!.disabled = !events.length
	}

	private submit() {
		const body = JSON.stringify({
			event: this.select.value,
			community: this.dialog.dataset.community,
		})
		const headers = { "Content-Type": "application/json", "X-Frappe-CSRF-Token": frappe.csrf_token }
		callApi("submit_event", { method: "POST", headers, body })
			.then(() => {
				this.form.hidden = true
				this.toggle("[data-submit-done]", true)
			})
			.catch((error: Error) => this.showError(error.message))
	}

	private showError(message: string) {
		this.error.textContent = message
		this.error.hidden = false
	}

	private toggle(selector: string, visible: boolean) {
		this.dialog.querySelector<HTMLElement>(selector)!.hidden = !visible
	}

	private reset() {
		this.form.hidden = false
		this.error.hidden = true
		this.toggle("[data-submit-done]", false)
	}
}
