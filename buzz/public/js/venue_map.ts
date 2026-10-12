// Opens a venue's locations on an interactive map. Frappe's own Leaflet bundle loads on the
// first open, so pages that never open the map never pay for it.

type VenueLocation = {
	venue_name: string
	label: string | null
	latitude: number | null
	longitude: number | null
	map_link: string | null
}

// Leaflet is a global from Frappe's bundle, with no types shipped for it.
// biome-ignore lint/suspicious/noExplicitAny: untyped third-party global
type Leaflet = any

// OSM's public tiles suit light traffic; a busier site moves to a hosted tile provider.
const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
const FIT_PADDING: [number, number] = [48, 48]
const MAX_ZOOM = 15
// Frappe ships Leaflet's marker images here; its bundled CSS cannot point Leaflet at them.
const MARKER_IMAGES = "/assets/frappe/images/leaflet/"

function loadOnce(element: HTMLScriptElement | HTMLLinkElement): Promise<void> {
	return new Promise((resolve, reject) => {
		element.addEventListener("load", () => resolve())
		element.addEventListener("error", () => reject(new Error("Leaflet failed to load")))
		document.head.append(element)
	})
}

function loadLeaflet(trigger: HTMLElement): Promise<Leaflet> {
	const leaflet = (window as unknown as { L?: Leaflet }).L
	if (leaflet) return Promise.resolve(leaflet)
	const script = Object.assign(document.createElement("script"), {
		src: trigger.dataset.leafletScript,
	})
	const style = Object.assign(document.createElement("link"), {
		rel: "stylesheet",
		href: trigger.dataset.leafletStyle,
	})
	return Promise.all([loadOnce(script), loadOnce(style)]).then(
		() => (window as unknown as { L: Leaflet }).L,
	)
}

// Built from text nodes, never HTML: names and labels are typed in by organisers.
function popupFor(location: VenueLocation): HTMLElement {
	const popup = document.createElement("div")
	if (location.label)
		popup.append(Object.assign(document.createElement("small"), { textContent: location.label }))
	const name = location.map_link
		? Object.assign(document.createElement("a"), {
				href: location.map_link,
				target: "_blank",
				rel: "noopener noreferrer",
			})
		: document.createElement("strong")
	name.textContent = location.venue_name
	popup.append(document.createElement("br"), name)
	return popup
}

class VenueMap {
	private map: Leaflet = null
	private readonly dialog: HTMLDialogElement
	private readonly locations: VenueLocation[]

	constructor(private readonly trigger: HTMLElement) {
		const block = trigger.closest(".venue") as HTMLElement
		this.dialog = block.querySelector("dialog") as HTMLDialogElement
		const data = block.querySelector("[data-venue-locations]")?.textContent || "[]"
		this.locations = (JSON.parse(data) as VenueLocation[]).filter(
			(location) => location.latitude && location.longitude,
		)
		trigger.addEventListener("click", () => this.open())
	}

	open() {
		this.dialog.showModal()
		loadLeaflet(this.trigger)
			.then((leaflet) => this.draw(leaflet))
			.catch(() => this.dialog.close())
	}

	draw(leaflet: Leaflet) {
		if (this.map) {
			this.map.invalidateSize()
			return
		}
		leaflet.Icon.Default.imagePath = MARKER_IMAGES
		const canvas = this.dialog.querySelector(".venue-map-canvas")
		this.map = leaflet.map(canvas)
		leaflet.tileLayer(TILE_URL, { attribution: ATTRIBUTION }).addTo(this.map)
		const points = this.locations.map((location) => {
			const point = [location.latitude, location.longitude]
			leaflet.marker(point).bindPopup(popupFor(location)).addTo(this.map)
			return point
		})
		this.map.fitBounds(points, { padding: FIT_PADDING, maxZoom: MAX_ZOOM })
	}
}

export function mountVenueMaps(): VenueMap[] {
	return [...document.querySelectorAll<HTMLElement>("[data-venue-map]")].map(
		(trigger) => new VenueMap(trigger),
	)
}
