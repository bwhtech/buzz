// The interactive half of the venue locations sheet, loaded on first open: a MapLibre map
// with a numbered marker per location, kept in step with the sheet's list.
import maplibregl from "maplibre-gl"

import type { LocationsMapView } from "./venue_map"

type VenueLocation = {
	venue_name: string
	label: string | null
	latitude: number | null
	longitude: number | null
}

// OpenFreeMap's hosted vector tiles: free, keyless and unmetered.
const MAP_STYLES = {
	dark: "https://tiles.openfreemap.org/styles/dark",
	light: "https://tiles.openfreemap.org/styles/positron",
}
const OSM_ATTRIBUTION =
	'<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">&copy; OpenStreetMap contributors</a>'
const FIT_PADDING = 64
const MAX_FIT_ZOOM = 13
const SELECTED_ZOOM = 14

function rowsOf(dialog: HTMLDialogElement): HTMLElement[] {
	return [...dialog.querySelectorAll<HTMLElement>("[data-location-index]")]
}

class LocationsMap implements LocationsMapView {
	private readonly map: maplibregl.Map
	private readonly markers = new Map<number, HTMLElement>()
	private readonly rows: HTMLElement[]
	private readonly locations: VenueLocation[]

	constructor(private readonly dialog: HTMLDialogElement) {
		const data = dialog.querySelector("[data-venue-locations]")?.textContent || "[]"
		this.locations = JSON.parse(data)
		this.rows = rowsOf(dialog)
		const canvas = dialog.querySelector<HTMLElement>("[data-venue-map-canvas]") as HTMLElement
		const mode = document.documentElement.dataset.mode === "light" ? "light" : "dark"
		this.map = new maplibregl.Map({
			container: canvas,
			style: MAP_STYLES[mode],
			bounds: this.bounds(),
			fitBoundsOptions: { padding: FIT_PADDING, maxZoom: MAX_FIT_ZOOM },
			// OpenStreetMap's data licence (ODbL) asks for its credit to stay in view.
			attributionControl: { compact: false, customAttribution: OSM_ATTRIBUTION },
		})
		this.map.once("load", () => canvas.toggleAttribute("data-ready", true))
		this.addMarkers()
		this.bindRows()
	}

	resize() {
		this.map.resize()
	}

	private pinned(): [number, VenueLocation][] {
		return [...this.locations.entries()].filter(
			([, location]) => location.latitude && location.longitude,
		)
	}

	private bounds(): maplibregl.LngLatBounds {
		const bounds = new maplibregl.LngLatBounds()
		for (const [, location] of this.pinned())
			bounds.extend([location.longitude!, location.latitude!])
		return bounds
	}

	private addMarkers() {
		for (const [index, location] of this.pinned()) {
			const element = this.markerElement(index, location)
			new maplibregl.Marker({ element })
				.setLngLat([location.longitude!, location.latitude!])
				.addTo(this.map)
			this.markers.set(index, element)
		}
	}

	private markerElement(index: number, location: VenueLocation): HTMLElement {
		const element = Object.assign(document.createElement("button"), { type: "button" })
		element.className = "venue-map-marker"
		element.setAttribute(
			"aria-label",
			[location.label, location.venue_name].filter(Boolean).join(", "),
		)
		const pin = Object.assign(document.createElement("span"), {
			className: "dot-map-pin",
			textContent: String(index + 1),
		})
		element.append(pin)
		this.bindHover(element, index)
		element.addEventListener("click", () => this.select(index))
		return element
	}

	private bindRows() {
		for (const row of this.rows) {
			const index = Number(row.dataset.locationIndex)
			const button = row.querySelector("button")
			this.bindHover(row, index)
			button?.addEventListener("focus", () => this.hover(index, true))
			button?.addEventListener("blur", () => this.hover(index, false))
			button?.addEventListener("click", () => this.select(index))
		}
	}

	private bindHover(element: HTMLElement, index: number) {
		element.addEventListener("pointerenter", () => this.hover(index, true))
		element.addEventListener("pointerleave", () => this.hover(index, false))
	}

	private hover(index: number, isHovered: boolean) {
		this.markers.get(index)?.toggleAttribute("data-hovered", isHovered)
		this.rows[index]?.toggleAttribute("data-hovered", isHovered)
	}

	private select(index: number) {
		for (const [markerIndex, marker] of this.markers)
			marker.toggleAttribute("data-selected", markerIndex === index)
		for (const row of this.rows) row.toggleAttribute("data-selected", row === this.rows[index])
		this.rows[index]?.scrollIntoView({ block: "nearest", behavior: "smooth" })
		const location = this.locations[index]
		// Not essential, so MapLibre jumps instead of flying when motion is reduced.
		this.map.flyTo({
			center: [location.longitude!, location.latitude!],
			zoom: Math.max(this.map.getZoom(), SELECTED_ZOOM),
			speed: 1.6,
			essential: false,
		})
	}
}

window.mountLocationsMap = (dialog: HTMLDialogElement) => new LocationsMap(dialog)
