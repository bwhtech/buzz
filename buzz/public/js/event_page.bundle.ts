import { bannerPattern } from "./event_banner"
import { EventCountdown } from "./event_countdown"
import { mountVenueMaps } from "./venue_map"

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
if (!customElements.get("event-countdown")) customElements.define("event-countdown", EventCountdown)

mountVenueMaps()
