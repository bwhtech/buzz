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

function loadMapBundle(trigger: HTMLElement): Promise<MountLocationsMap> {
	if (window.mountLocationsMap) return Promise.resolve(window.mountLocationsMap)
	const script = Object.assign(document.createElement("script"), { src: trigger.dataset.mapScript })
	const style = Object.assign(document.createElement("link"), {
		rel: "stylesheet",
		href: trigger.dataset.mapStyle,
	})
	return Promise.all([load(script), load(style)]).then(
		() => window.mountLocationsMap as MountLocationsMap,
	)
}

class VenueMapDialog {
	private view: LocationsMapView | null = null
	private readonly dialog: HTMLDialogElement

	constructor(private readonly trigger: HTMLElement) {
		this.dialog = trigger.parentElement?.querySelector(".venue-map-dialog") as HTMLDialogElement
		trigger.addEventListener("click", () => this.open())
		// A click on the backdrop lands on the dialog itself, outside the sheet.
		this.dialog.addEventListener("click", (click) => {
			if (click.target === this.dialog) this.dialog.close()
		})
	}

	open() {
		this.dialog.showModal()
		if (this.view) {
			this.view.resize()
			return
		}
		// Without the map (offline, or no WebGL) the list of locations still stands on its own.
		loadMapBundle(this.trigger)
			.then((mount) => {
				this.view = mount(this.dialog)
			})
			.catch(() =>
				this.dialog.querySelector("[data-venue-map-canvas]")?.toggleAttribute("data-failed", true),
			)
	}
}

export function mountVenueMaps(): VenueMapDialog[] {
	return [...document.querySelectorAll<HTMLElement>("[data-venue-map]")].map(
		(trigger) => new VenueMapDialog(trigger),
	)
}
