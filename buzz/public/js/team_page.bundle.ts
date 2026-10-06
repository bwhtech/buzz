// Upcoming / Past on a team page: espresso tab buttons that switch panels.
const pills = [...document.querySelectorAll<HTMLButtonElement>("[data-tab-buttons] .es-pill")]

function showPanel(name: string) {
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

for (const pill of pills) {
	pill.addEventListener("click", () => showPanel(pill.dataset.tab || ""))
	pill.addEventListener("keydown", (event) => {
		if (event.key === "ArrowRight") moveFocus(pill, 1)
		if (event.key === "ArrowLeft") moveFocus(pill, -1)
	})
}
