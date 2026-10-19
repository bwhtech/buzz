import type { Marker } from "cobe"

const LARGE = 0.07
const SMALL = 0.045
const GROW_MS = 600
const FIRST_STAGGER_MS = 140
// A city counts as facing the viewer once the cosine of its distance from the front meridian
// passes this, a little before it clears the globe's edge.
const FACING = 0.3

// Latitude, longitude, size. At most 32: see padded().
const CITIES: [number, number, number][] = [
	[52.5, 13.4, LARGE],
	[12.97, 77.6, LARGE],
	[37.8, -122.4, LARGE],
	[35.7, 139.7, LARGE],
	[-33.9, 151.2, LARGE],
	[51.5, -0.1, SMALL],
	[40.7, -74, LARGE],
	[19.4, -99.1, SMALL],
	[1.35, 103.8, SMALL],
	[48.86, 2.35, SMALL],
	[6.52, 3.38, LARGE],
	[-1.29, 36.82, SMALL],
	[30.04, 31.24, SMALL],
	[25.2, 55.27, SMALL],
	[19.08, 72.88, LARGE],
	[28.61, 77.21, SMALL],
	[-6.2, 106.85, SMALL],
	[37.57, 126.98, SMALL],
	[14.6, 120.98, SMALL],
	[31.23, 121.47, LARGE],
	[-37.81, 144.96, SMALL],
	[-36.85, 174.76, SMALL],
	[-23.55, -46.63, LARGE],
	[-34.6, -58.38, SMALL],
	[4.71, -74.07, SMALL],
	[43.65, -79.38, SMALL],
	[30.27, -97.74, SMALL],
	[47.61, -122.33, SMALL],
	[38.72, -9.14, SMALL],
	[59.33, 18.07, SMALL],
	[-33.92, 18.42, SMALL],
	[41.01, 28.98, SMALL],
]

const easeOut = (progress: number) => 1 - (1 - Math.min(progress, 1)) ** 3

// Cities pop onto the globe as the spin first brings each one round to the front.
export class MarkerReveal {
	private shownAt = new Map<number, number>()
	private isComplete = false

	constructor(private skipAnimation: boolean) {}

	// The markers as they stand, for a redraw. Unpadded: cobe counts its options correctly.
	current(now: number): Marker[] {
		return CITIES.map(([latitude, longitude, size], index) => ({
			location: [latitude, longitude],
			size: this.skipAnimation ? size : size * easeOut(this.progress(index, now)),
		}))
	}

	// What onRender hands cobe, or undefined once every city is in and nothing changes.
	update(phi: number, now: number): Marker[] | undefined {
		if (this.isComplete) return undefined
		this.revealFacing(phi, now)
		this.isComplete =
			this.skipAnimation || CITIES.every((_, index) => this.progress(index, now) >= 1)
		return padded(this.current(now))
	}

	private revealFacing(phi: number, now: number) {
		const isFirstFrame = this.shownAt.size === 0
		let order = 0
		CITIES.forEach(([, longitude], index) => {
			if (this.shownAt.has(index) || !isFacing(longitude, phi)) return
			this.shownAt.set(index, now + (isFirstFrame ? order++ * FIRST_STAGGER_MS : 0))
		})
	}

	private progress(index: number, now: number): number {
		const shownAt = this.shownAt.get(index)
		return shownAt === undefined ? 0 : Math.max(0, now - shownAt) / GROW_MS
	}
}

// cobe faces longitude 3π/2 − phi towards the viewer.
function isFacing(longitude: number, phi: number): boolean {
	return Math.cos((longitude * Math.PI) / 180 - (1.5 * Math.PI - phi)) > FACING
}

// cobe 0.6.5 sizes a marker update at half the slots it fills, so it would drop the second
// half of the list. Zero-size padding takes that half.
function padded(markers: Marker[]): Marker[] {
	return [...markers, ...markers.map((marker) => ({ ...marker, size: 0 }))]
}
