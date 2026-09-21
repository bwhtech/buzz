import { bannerPattern } from "./event_banner"

// Also read by the inline script in the layout's <head>, which applies it before first paint.
const MODE_STORAGE_KEY = "buzz-page-mode"

// The public page's theme tokens, so each theme colours the same rings its own way.
const PAGE_COLOURS = { line: "var(--border)", surface: "var(--surface)" }

class EventBanner extends HTMLElement {
	static observedAttributes = ["seed"]

	connectedCallback() {
		this.draw()
	}

	attributeChangedCallback() {
		this.draw()
	}

	draw() {
		this.style.backgroundImage = bannerPattern(
			this.getAttribute("seed") || "Untitled",
			PAGE_COLOURS,
		)
	}
}

if (!customElements.get("event-banner")) customElements.define("event-banner", EventBanner)

function setMode(toggle: HTMLElement, mode: string) {
	document.documentElement.dataset.mode = mode
	toggle.setAttribute("aria-pressed", String(mode === "dark"))
}

function toggleMode(toggle: HTMLElement) {
	const mode = document.documentElement.dataset.mode === "dark" ? "light" : "dark"
	setMode(toggle, mode)
	try {
		localStorage.setItem(MODE_STORAGE_KEY, mode)
	} catch {
		// Storage can be blocked; the switch still holds for this page view.
	}
}

const modeToggle = document.querySelector<HTMLElement>("[data-mode-toggle]")
if (modeToggle) {
	setMode(modeToggle, document.documentElement.dataset.mode || "dark")
	modeToggle.addEventListener("click", () => toggleMode(modeToggle))
}
