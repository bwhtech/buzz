import { formatTimeLeft } from "./time_left"

const SECOND = 1000
const BLURRED = { opacity: 0, filter: "blur(4px)" }
const SHARP = { opacity: 1, filter: "blur(0)" }
const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)"
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)")

// Each changed character rolls down into place; inline-grid slots collapse a plain space.
class RollingText {
	constructor(private element: HTMLElement) {}

	set(value: string) {
		const text = value.replaceAll(" ", "\u00a0")
		const slots = [...this.element.children] as HTMLElement[]
		if (slots.length !== text.length) {
			this.element.replaceChildren(...[...text].map((character) => this.slot(character)))
			return
		}
		;[...text].forEach((character, index) => this.roll(slots[index], character))
	}

	private slot(character: string): HTMLElement {
		const slot = document.createElement("span")
		slot.className = "roll-slot"
		slot.dataset.character = character
		slot.append(this.glyph(character))
		return slot
	}

	private glyph(character: string, className = ""): HTMLElement {
		const glyph = document.createElement("span")
		glyph.className = className
		glyph.textContent = character
		return glyph
	}

	private roll(slot: HTMLElement, character: string) {
		if (slot.dataset.character === character) return
		slot.dataset.character = character
		const outgoing = slot.lastElementChild as HTMLElement
		outgoing.className = "roll-out"
		// Reduced motion turns the roll off, and with it animationend.
		if (reduceMotion.matches) outgoing.remove()
		else outgoing.addEventListener("animationend", () => outgoing.remove(), { once: true })
		slot.append(this.glyph(character, "roll-in"))
	}
}

// The pill on an event's banner: time left until the start on the viewer's own clock, then
// Live until the end. The server leaves it out once the event is over.
export class EventCountdown extends HTMLElement {
	private timer = 0
	private label = ""
	private value?: RollingText

	connectedCallback() {
		const value = this.querySelector<HTMLElement>(".countdown-value")
		if (!value) return
		this.value = new RollingText(value)
		this.label = this.querySelector(".countdown-upcoming")?.firstChild?.textContent?.trim() || ""
		this.tick()
		this.hidden = false
	}

	disconnectedCallback() {
		clearTimeout(this.timer)
	}

	private tick = () => {
		if (!this.render(Date.now())) return
		this.timer = window.setTimeout(this.tick, SECOND - (Date.now() % SECOND))
	}

	/** Returns false once the event has ended and the pill is gone. */
	private render(now: number): boolean {
		const startsAt = Date.parse(this.getAttribute("starts-at") || "")
		const endsAt = Date.parse(this.getAttribute("ends-at") || "")
		if (now >= endsAt) {
			this.remove()
			return false
		}
		const isLive = now >= startsAt
		this.setLive(isLive)
		if (isLive) {
			this.removeAttribute("aria-label")
			return true
		}
		const timeLeft = formatTimeLeft(startsAt - now)
		this.value?.set(timeLeft)
		this.setAttribute("aria-label", `${this.label} ${timeLeft}`)
		return true
	}

	// A short blur crossfade carries the switch to Live; the first render, still hidden, just sets it.
	private setLive(isLive: boolean) {
		if (isLive === this.hasAttribute("data-live")) return
		const swap = () => this.toggleAttribute("data-live", isLive)
		if (this.hidden || reduceMotion.matches) return swap()
		this.animate([SHARP, BLURRED], { duration: 120, easing: EASE_OUT }).finished.then(() => {
			swap()
			this.animate([BLURRED, SHARP], { duration: 200, easing: EASE_OUT })
		})
	}
}
