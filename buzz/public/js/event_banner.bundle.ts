import { bannerPattern } from "./event_banner"

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
