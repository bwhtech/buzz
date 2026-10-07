import { type EventCard, formatDay, reducedMotion } from "./page_data"
import { findEventCard, scrollAndHighlight } from "./timeline"

interface View {
	x: number
	y: number
	w: number
	h: number
}

interface Pin {
	element: HTMLAnchorElement
	x: number
	y: number
	country: string | null
	events: EventCard[]
	tooltip: HTMLElement
	locationLabel: string
}

// The equirectangular world, x = longitude + 180 and y = 90 - latitude, cropped to land.
const WORLD_VIEW: View = { x: 0, y: 6, w: 360, h: 140 }
const ZOOM_DURATION_MILLISECONDS = 420
// The narrowest frame, in degrees: one country on its own is too few dots to read as land.
const MINIMUM_VIEW_WIDTH = 60
// Everywhere frames a little wider than one country, so it differs from Nearby even when
// every event is in the same city.
const EVERYWHERE_MINIMUM_VIEW_WIDTH = 100
// Land dots sit on a 1.2° grid and grow with the zoom, within a readable range of sizes.
const GRID_DEGREES = 1.2
const DOT_SHARE_OF_GRID = 0.2
const DOT_PIXELS = { minimum: 2.5, maximum: 6 }
// Within this many pixels of an edge, a tooltip turns away from it.
const TOOLTIP_EDGE_DISTANCE = { top: 96, side: 120 }

const easeOut = (progress: number) => 1 - (1 - progress) ** 3

function createElement<K extends keyof HTMLElementTagNameMap>(
	tag: K,
	className: string,
	text = "",
) {
	return Object.assign(document.createElement(tag), { className, textContent: text })
}

function groupByLocation(events: EventCard[]): EventCard[][] {
	const locations = new Map<string, EventCard[]>()
	for (const event of events) {
		// Two Cambridges are two locations; a venue without a city is its own location.
		const location = event.city
			? `${event.city}|${event.country}`
			: `${event.latitude},${event.longitude}`
		locations.set(location, [...(locations.get(location) || []), event])
	}
	return [...locations.values()]
}

// A pin can hold several events; its tooltip shows one of them at a time.
function fillTooltip(tooltip: HTMLElement, event: EventCard, locationLabel: string) {
	tooltip.replaceChildren(
		createElement("strong", "", locationLabel),
		createElement("span", "", event.title),
		createElement("span", "", `${formatDay(event.date)} · ${event.time}`),
	)
}

function createPin(events: EventCard[], isNextEvent: boolean): Pin {
	const [first] = events
	const locationLabel = first.city || first.country || ""
	const link = createElement("a", "team-map-pin")
	link.href = first.url
	link.toggleAttribute("data-next-event", isNextEvent)
	link.setAttribute("aria-label", `${locationLabel}: ${first.title}`)
	const count = events.length > 1 ? String(events.length) : ""
	const tooltip = createElement("span", "team-map-pin-tooltip")
	fillTooltip(tooltip, first, locationLabel)
	link.append(createElement("span", "team-map-pin-dot", count), tooltip)
	link.addEventListener("click", (click) => {
		const card = findEventCard(first.route)
		if (!card?.offsetParent) return
		click.preventDefault()
		scrollAndHighlight(card)
	})
	return {
		element: link,
		x: first.longitude! + 180,
		y: 90 - first.latitude!,
		country: first.country,
		events,
		tooltip,
		locationLabel,
	}
}

/** The dot-matrix map: a pin per location, framed on a country by animating the viewBox. */
export class TeamMap {
	private svg: SVGSVGElement
	private dots: SVGUseElement | null
	private pins: Pin[]
	private view: View
	private country = ""
	private frame = 0

	constructor(
		private root: HTMLElement,
		upcoming: EventCard[],
	) {
		this.svg = root.querySelector("svg")!
		this.dots = root.querySelector<SVGUseElement>(".team-map-land")
		const locations = groupByLocation(upcoming.filter((event) => event.latitude !== null))
		this.pins = locations.map((events, index) => createPin(events, index === 0))
		root.querySelector(".team-map-pins")!.append(...this.pins.map((pin) => pin.element))
		this.view = this.targetView()
		this.render()
		new ResizeObserver(() => this.showView(this.targetView())).observe(root)
	}

	filterByCountry(country: string) {
		this.country = country
		for (const pin of this.pins) {
			pin.element.toggleAttribute("data-dimmed", Boolean(country) && pin.country !== country)
		}
		this.animateToView(this.targetView())
	}

	// A hovered card lights its pin, which then shows that card's event rather than the next one.
	highlightEvent(route: string | null) {
		for (const pin of this.pins) {
			const event = pin.events.find((pinEvent) => pinEvent.route === route)
			pin.element.toggleAttribute("data-highlighted", Boolean(event))
			fillTooltip(pin.tooltip, event || pin.events[0], pin.locationLabel)
		}
	}

	// Frames the pins in view with some padding: one country's, or every pin.
	private targetView(): View {
		const pins = this.pins.filter((pin) => !this.country || pin.country === this.country)
		if (!pins.length || !this.root.clientWidth) return this.fitToAspectRatio(WORLD_VIEW)
		const xs = pins.map((pin) => pin.x)
		const ys = pins.map((pin) => pin.y)
		const [left, right, top, bottom] = [
			Math.min(...xs),
			Math.max(...xs),
			Math.min(...ys),
			Math.max(...ys),
		]
		const minimumWidth = this.country ? MINIMUM_VIEW_WIDTH : EVERYWHERE_MINIMUM_VIEW_WIDTH
		const w = Math.max(right - left + 16, minimumWidth)
		const h = Math.max(bottom - top + 12, 16)
		return this.fitToAspectRatio({ x: (left + right - w) / 2, y: (top + bottom - h) / 2, w, h })
	}

	// Grows the box on one axis to the strip's aspect ratio, so `slice` never crops a pin away.
	private fitToAspectRatio(view: View): View {
		const aspectRatio = this.root.clientWidth / this.root.clientHeight || 2
		const w = Math.max(view.w, view.h * aspectRatio)
		const h = Math.max(view.h, view.w / aspectRatio)
		return { x: view.x + (view.w - w) / 2, y: view.y + (view.h - h) / 2, w, h }
	}

	private showView(view: View) {
		cancelAnimationFrame(this.frame)
		this.view = view
		this.render()
	}

	private animateToView(view: View) {
		if (reducedMotion.matches) return this.showView(view)
		cancelAnimationFrame(this.frame)
		const from = { ...this.view }
		const start = performance.now()
		const step = (now: number) => {
			const progress = easeOut(Math.min(1, (now - start) / ZOOM_DURATION_MILLISECONDS))
			for (const key of ["x", "y", "w", "h"] as const)
				this.view[key] = from[key] + (view[key] - from[key]) * progress
			this.render()
			if (progress < 1) this.frame = requestAnimationFrame(step)
		}
		this.frame = requestAnimationFrame(step)
	}

	private render() {
		const { x, y, w, h } = this.view
		this.svg.setAttribute("viewBox", `${x} ${y} ${w} ${h}`)
		const { clientWidth: width, clientHeight: height } = this.root
		const scale = Math.max(width / w, height / h)
		this.sizeDots(scale)
		for (const pin of this.pins) {
			const left = (width - w * scale) / 2 + (pin.x - x) * scale
			this.positionPin(pin, left, (height - h * scale) / 2 + (pin.y - y) * scale)
		}
	}

	// Stroke width is in map units, so a dot's pixel size is its width times the scale.
	private sizeDots(scale: number) {
		const pixels = Math.min(
			Math.max(GRID_DEGREES * scale * DOT_SHARE_OF_GRID, DOT_PIXELS.minimum),
			DOT_PIXELS.maximum,
		)
		this.dots?.setAttribute("stroke-width", String(pixels / scale))
	}

	private positionPin(pin: Pin, left: number, top: number) {
		pin.element.style.transform = `translate(${left}px, ${top}px)`
		pin.element.toggleAttribute("data-tooltip-below", top < TOOLTIP_EDGE_DISTANCE.top)
		const { side } = TOOLTIP_EDGE_DISTANCE
		const width = this.root.clientWidth
		pin.element.dataset.tooltipAlign =
			left < side ? "start" : left > width - side ? "end" : "center"
	}
}
