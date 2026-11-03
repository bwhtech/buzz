// Opens a venue's locations in a sheet beside an interactive map. The map's bundle loads on
// the first open, so pages that never open it never pay for it.

export interface LocationsMapView {
	resize(): void
}

type MountLocationsMap = (dialog: HTMLDialogElement) => LocationsMapView

declare global {
	interface Window {
		mountLocationsMap?: MountLocationsMap
	}
}

function load(element: HTMLScriptElement | HTMLLinkElement): Promise<void> {
	return new Promise((resolve, reject) => {
		element.addEventListener("load", () => resolve())
		element.addEventListener("error", () => reject(new Error("The map failed to load")))
		document.head.append(element)
	})
}

function loadMapBundle(dialog: HTMLElement): Promise<MountLocationsMap> {
	if (window.mountLocationsMap) return Promise.resolve(window.mountLocationsMap)
	const script = Object.assign(document.createElement("script"), { src: dialog.dataset.mapScript })
	const style = Object.assign(document.createElement("link"), {
		rel: "stylesheet",
		href: dialog.dataset.mapStyle,
	})
	return Promise.all([load(script), load(style)]).then(
		() => window.mountLocationsMap as MountLocationsMap,
	)
}

// Emails and the dashboard link here to open the locations straight away.
const LOCATIONS_HASH = "#locations"

class VenueMapDialog {
	private view: LocationsMapView | null = null

	constructor(
		private readonly dialog: HTMLDialogElement,
		triggers: HTMLElement[],
	) {
		for (const trigger of triggers) trigger.addEventListener("click", () => this.open())
		// A click on the backdrop lands on the dialog itself, outside the sheet.
		this.dialog.addEventListener("click", (click) => {
			if (click.target === this.dialog) this.dialog.close()
		})
		window.addEventListener("hashchange", () => this.openFromHash())
		this.openFromHash()
	}

	openFromHash() {
		if (window.location.hash === LOCATIONS_HASH && !this.dialog.open) this.open()
	}

	open() {
		this.dialog.showModal()
		if (this.view) {
			this.view.resize()
			return
		}
		// A venue with no coordinates has no map; its list stands on its own.
		if (!this.dialog.dataset.mapScript) return
		// Without the map (offline, or no WebGL) the list of locations still stands on its own.
		loadMapBundle(this.dialog)
			.then((mount) => {
				this.view = mount(this.dialog)
			})
			.catch(() =>
				this.dialog.querySelector("[data-venue-map-canvas]")?.toggleAttribute("data-failed", true),
			)
	}
}

export function mountVenueMaps(): VenueMapDialog | null {
	const dialog = document.querySelector<HTMLDialogElement>("#venue-locations")
	if (!dialog) return null
	return new VenueMapDialog(dialog, [...document.querySelectorAll<HTMLElement>("[data-venue-map]")])
}
