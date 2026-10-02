import { bannerPattern } from "./event_banner"

// The key frappe-ui's useColorScheme keeps the dashboard's choice under, so both share one.
// Also read by the inline script in the layout's <head>, which applies it before first paint.
const MODE_STORAGE_KEY = "theme"

// The public page's theme tokens, so each theme colours the same rings its own way.
const PAGE_COLOURS = { line: "var(--border)", surface: "var(--surface)" }

class EventBanner extends HTMLElement {
	static observedAttributes = ["seed"]

	connectedCallback() {
		this.draw()
	}

	attributeChangedCallback() {
		this.draw()
	}

	draw() {
		this.style.backgroundImage = bannerPattern(
			this.getAttribute("seed") || "Untitled",
			PAGE_COLOURS,
		)
	}
}

if (!customElements.get("event-banner")) customElements.define("event-banner", EventBanner)

function setMode(toggle: HTMLElement, mode: string) {
	document.documentElement.dataset.mode = mode
	toggle.setAttribute("aria-pressed", String(mode === "dark"))
}

function toggleMode(toggle: HTMLElement) {
	const mode = document.documentElement.dataset.mode === "dark" ? "light" : "dark"
	// A crossfade hides the whole palette swapping in one frame; skipped for reduced motion.
	const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches
	if ("startViewTransition" in document && !reduceMotion) {
		document.startViewTransition(() => setMode(toggle, mode))
	} else {
		setMode(toggle, mode)
	}
	try {
		localStorage.setItem(MODE_STORAGE_KEY, mode)
	} catch {
		// Storage can be blocked; the switch still holds for this page view.
	}
}

const modeToggle = document.querySelector<HTMLElement>("[data-mode-toggle]")
if (modeToggle) {
	setMode(modeToggle, document.documentElement.dataset.mode || "dark")
	modeToggle.addEventListener("click", () => toggleMode(modeToggle))
}

const LOGIN_MESSAGE = "buzz-login"
const LOGIN_FRAME_FADE_MS = 150

function openLoginFrame(link: HTMLAnchorElement) {
	// A frame still here never became ready (the embed failed to load), so start over.
	document.querySelector(".login-frame")?.remove()
	const mode = document.documentElement.dataset.mode === "light" ? "light" : "dark"
	const frame = document.createElement("iframe")
	frame.className = "login-frame"
	frame.title = link.textContent?.trim() || ""
	frame.style.colorScheme = mode
	frame.src = `/b/login/embed?mode=${mode}`
	document.body.append(frame)
}

function closeLoginFrame(frame: HTMLIFrameElement) {
	frame.removeAttribute("data-ready")
	setTimeout(() => frame.remove(), LOGIN_FRAME_FADE_MS)
	document.querySelector<HTMLAnchorElement>("a[data-login]")?.focus()
}

window.addEventListener("message", (event) => {
	if (event.origin !== location.origin || event.data?.type !== LOGIN_MESSAGE) return
	const frame = document.querySelector<HTMLIFrameElement>(".login-frame")
	if (!frame || event.source !== frame.contentWindow) return
	if (event.data.state === "ready") {
		frame.setAttribute("data-ready", "")
		frame.focus()
	} else if (event.data.state === "success") {
		location.reload()
	} else if (event.data.state === "close") {
		closeLoginFrame(frame)
	}
})

document.querySelectorAll<HTMLAnchorElement>("a[data-login]").forEach((link) => {
	link.addEventListener("click", (event) => {
		if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
		event.preventDefault()
		openLoginFrame(link)
	})
})
