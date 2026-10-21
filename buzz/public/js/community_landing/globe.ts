import createGlobe, { type COBEOptions } from "cobe"

import { reducedMotion } from "../team_page/page_data"
import { MarkerReveal } from "./markers"

type Globe = ReturnType<typeof createGlobe>
type ThemeOptions = Pick<
	COBEOptions,
	"dark" | "diffuse" | "mapBrightness" | "baseColor" | "glowColor"
>

const ACCENT: [number, number, number] = [0.95, 0.42, 0.1]
const AUTO_ROTATE_SPEED = 0.0028
const DRAG_SENSITIVITY = 220
const MOMENTUM_DECAY = 0.94

const LIGHT: ThemeOptions = {
	dark: 0,
	diffuse: 0.6,
	mapBrightness: 1.4,
	baseColor: [1, 1, 1],
	glowColor: [0.96, 0.96, 0.96],
}

const DARK: ThemeOptions = {
	dark: 1,
	diffuse: 1.4,
	mapBrightness: 5,
	baseColor: [0.32, 0.32, 0.32],
	glowColor: [0.16, 0.16, 0.16],
}

// A draggable globe that drifts on its own, keeps a flick's momentum, and redraws when the page
// switches between light and dark.
export class CommunityGlobe {
	private globe: Globe | null = null
	private phi = 4.6
	private velocity = 0
	private dragX: number | null = null
	private isVisible = true
	private markers = new MarkerReveal(reducedMotion.matches)

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
			markers: this.markers.current(performance.now()),
			onRender: (state) => this.onRender(state),
		})
		this.globe.toggle(this.isVisible)
		requestAnimationFrame(() => this.canvas.toggleAttribute("data-ready", true))
	}

	private onRender(state: Record<string, unknown>) {
		if (this.dragX === null) {
			this.velocity *= MOMENTUM_DECAY
			this.phi += (reducedMotion.matches ? 0 : AUTO_ROTATE_SPEED) + this.velocity
		}
		state.phi = this.phi
		const markers = this.markers.update(this.phi, performance.now())
		if (markers) state.markers = markers
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
