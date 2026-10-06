import { reducedMotion } from "./page_data"

const pills = [...document.querySelectorAll<HTMLButtonElement>("[data-tab-buttons] .es-pill")]

export function showPanel(name: string) {
	for (const pill of pills) {
		const active = pill.dataset.tab === name
		pill.dataset.state = active ? "active" : "inactive"
		pill.setAttribute("aria-checked", String(active))
		pill.tabIndex = active ? 0 : -1
	}
	for (const panel of document.querySelectorAll<HTMLElement>("[data-panel]")) {
		panel.hidden = panel.dataset.panel !== name
	}
}

// Arrow keys move within the group, as a radiogroup expects.
function moveFocus(from: HTMLButtonElement, offset: number) {
	const next = pills[(pills.indexOf(from) + offset + pills.length) % pills.length]
	showPanel(next.dataset.tab || "")
	next.focus()
}

export function wireTabs() {
	for (const pill of pills) {
		pill.addEventListener("click", () => showPanel(pill.dataset.tab || ""))
		pill.addEventListener("keydown", (event) => {
			if (event.key === "ArrowRight") moveFocus(pill, 1)
			if (event.key === "ArrowLeft") moveFocus(pill, -1)
		})
	}
}

export function findEventCard(route: string): HTMLElement | null {
	return document.querySelector<HTMLElement>(`[data-event-route="${CSS.escape(route)}"]`)
}

// A brief ring, so the eye lands on what a calendar day or a pin pointed at.
export function scrollAndHighlight(element: HTMLElement) {
	element.scrollIntoView({ behavior: reducedMotion.matches ? "auto" : "smooth", block: "center" })
	element.classList.remove("is-highlighted")
	requestAnimationFrame(() => element.classList.add("is-highlighted"))
}
