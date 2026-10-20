// The /community landing page: the hero globe and the feature demos. team_page.bundle.ts runs the preview.
import { CommunityGlobe } from "./community_landing/globe"

const canvas = document.querySelector<HTMLCanvasElement>("[data-globe]")
// Without WebGL the hero closes up instead of leaving a blank horizon. The probe uses a spare
// canvas: probing the real one would fix its context before cobe asks for its own options.
const hasWebGL = Boolean(document.createElement("canvas").getContext("webgl"))
if (canvas && hasWebGL) CommunityGlobe.mount(canvas)
else canvas?.parentElement?.setAttribute("hidden", "")

// Each demo plays once: pressing its button shows the outcome.
for (const trigger of document.querySelectorAll<HTMLElement>("[data-demo-trigger]")) {
	trigger.addEventListener("click", () => {
		trigger.closest<HTMLElement>("[data-demo]")?.setAttribute("data-demo", "on")
	})
}

// Follow is a mock: every Follow button on the page toggles one shared state.
const landing = document.querySelector<HTMLElement>("[data-following]")
for (const button of document.querySelectorAll<HTMLButtonElement>("[data-follow]")) {
	button.addEventListener("click", () => {
		const following = landing?.dataset.following !== "true"
		landing?.setAttribute("data-following", String(following))
		for (const each of document.querySelectorAll("[data-follow]")) {
			each.setAttribute("aria-pressed", String(following))
			each.setAttribute("data-variant", following ? "subtle" : "solid")
		}
	})
}

// The closing call to action, and a return from login or signup, open the hero's dialog.
const createTrigger = document.querySelector<HTMLElement>('[data-island="create-community"]')
for (const button of document.querySelectorAll<HTMLElement>("[data-create-community]")) {
	button.addEventListener("click", () => createTrigger?.click())
}
if (new URLSearchParams(window.location.search).has("create")) {
	window.addEventListener("load", () => createTrigger?.click())
}
