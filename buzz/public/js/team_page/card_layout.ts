// The Timeline / Cards switch. The choice shares its key with the dashboard's useEventCardLayout,
// so a viewer sees the same shape on both; the timeline macro applies it before first paint.
type CardLayout = "row" | "cover"

const STORAGE_KEY = "buzz:event-card-layout"
const buttons = [...document.querySelectorAll<HTMLButtonElement>("[data-layout-buttons] .es-pill")]

function storedLayout(): CardLayout {
	try {
		return localStorage.getItem(STORAGE_KEY) === "cover" ? "cover" : "row"
	} catch {
		return "row"
	}
}

function applyLayout(layout: CardLayout) {
	document.documentElement.dataset.cardLayout = layout
	for (const card of document.querySelectorAll<HTMLElement>("[data-event-card]")) {
		card.dataset.layout = layout
	}
	for (const button of buttons) {
		const active = button.dataset.cardLayout === layout
		button.dataset.state = active ? "active" : "inactive"
		button.setAttribute("aria-checked", String(active))
		button.tabIndex = active ? 0 : -1
	}
}

function chooseLayout(layout: CardLayout) {
	applyLayout(layout)
	try {
		localStorage.setItem(STORAGE_KEY, layout)
	} catch {
		// Private windows can refuse storage; the switch still works for this visit.
	}
}

export function wireCardLayout() {
	applyLayout(storedLayout())
	for (const button of buttons) {
		const layout = button.dataset.cardLayout as CardLayout
		button.addEventListener("click", () => chooseLayout(layout))
		button.addEventListener("keydown", (event) => {
			if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return
			const next = buttons.find((other) => other !== button)
			chooseLayout(next?.dataset.cardLayout as CardLayout)
			next?.focus()
		})
	}
}
