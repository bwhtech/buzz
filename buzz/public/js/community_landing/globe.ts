import createGlobe, { type COBEOptions, type Marker } from "cobe"

import { reducedMotion } from "../team_page/page_data"

type Globe = ReturnType<typeof createGlobe>

const ACCENT: [number, number, number] = [0.95, 0.42, 0.1]
const AUTO_ROTATE_SPEED = 0.0028
const DRAG_SENSITIVITY = 220
const MOMENTUM_DECAY = 0.94

const MARKERS: Marker[] = [
	[52.5, 13.4, 0.07],
	[12.97, 77.6, 0.07],
	[37.8, -122.4, 0.07],
	[35.7, 139.7, 0.07],
	[51.5, -0.1, 0.045],
	[40.7, -74, 0.045],
	[-33.9, 151.2, 0.07],
	[19.4, -99.1, 0.045],
	[1.35, 103.8, 0.045],
].map(([latitude, longitude, size]): Marker => ({ location: [latitude, longitude], size }))

const LIGHT = {
	dark: 0,
	diffuse: 0.6,
	mapBrightness: 1.4,
	baseColor: [1, 1, 1],
	glowColor: [0.96, 0.96, 0.96],
} satisfies Partial<COBEOptions>

const DARK = {
	dark: 1,
	diffuse: 1.4,
	mapBrightness: 5,
	baseColor: [0.32, 0.32, 0.32],
	glowColor: [0.16, 0.16, 0.16],
} satisfies Partial<COBEOptions>

// A draggable globe that drifts on its own, keeps a flick's momentum, and redraws when the page
// switches between light and dark.
export class CommunityGlobe {
	private globe: Globe | null = null
	private phi = 4.6
	private velocity = 0
	private dragX: number | null = null
	private isVisible = true

	static mount(canvas: HTMLCanvasElement): CommunityGlobe {
		return new CommunityGlobe(canvas)
	}

	private constructor(private canvas: HTMLCanvasElement) {
		this.wireDrag()
		new MutationObserver(() => this.draw()).observe(document.documentElement, {
			attributeFilter: ["data-mode"],
		})
		// Off screen, the globe stops drawing frames.
		new IntersectionObserver(([entry]) => {
			this.isVisible = entry.isIntersecting
			this.globe?.toggle(this.isVisible)
		}).observe(canvas)
		this.draw()
	}

	private draw() {
		this.globe?.destroy()
		const isDark = document.documentElement.dataset.mode === "dark"
		this.globe = createGlobe(this.canvas, {
			...(isDark ? DARK : LIGHT),
			devicePixelRatio: 2,
			width: this.size(),
			height: this.size(),
			phi: this.phi,
			theta: 0.28,
			mapSamples: 28000,
			markerColor: ACCENT,
			markers: MARKERS,
			onRender: (state) => this.onRender(state),
		})
		this.globe.toggle(this.isVisible)
		requestAnimationFrame(() => this.canvas.toggleAttribute("data-ready", true))
	}

	private onRender(state: Record<string, number>) {
		if (this.dragX === null) {
			this.velocity *= MOMENTUM_DECAY
			this.phi += (reducedMotion.matches ? 0 : AUTO_ROTATE_SPEED) + this.velocity
		}
		state.phi = this.phi
		state.width = this.size()
		state.height = this.size()
	}

	private size(): number {
		return this.canvas.offsetWidth * 2
	}

	private wireDrag() {
		this.canvas.addEventListener("pointerdown", (event) => {
			if (this.dragX !== null) return
			this.dragX = event.clientX
			this.canvas.setPointerCapture(event.pointerId)
			this.canvas.toggleAttribute("data-dragging", true)
		})
		this.canvas.addEventListener("pointermove", (event) => {
			if (this.dragX === null) return
			const delta = (event.clientX - this.dragX) / DRAG_SENSITIVITY
			this.dragX = event.clientX
			this.velocity = delta
			this.phi += delta
		})
		for (const type of ["pointerup", "pointercancel"]) {
			this.canvas.addEventListener(type, () => this.endDrag())
		}
	}

	private endDrag() {
		this.dragX = null
		this.canvas.toggleAttribute("data-dragging", false)
	}
}
