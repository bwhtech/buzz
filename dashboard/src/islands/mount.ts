import { FrappeUIProvider, portalTargetKey } from "frappe-ui"
import { type Component, createApp, h, type Ref, ref } from "vue"

import "./islands.css"
import { translate } from "./translate"

type Loader = () => Promise<{ default: Component }>

// Each island's name, as a page's data-island names it, to its component.
const ISLANDS: Record<string, Loader> = {
	"add-event": () => import("@/components/dashboard/teams/AddEventMenu.vue"),
}

const opened = new Map<HTMLElement, Ref<boolean>>()

// Public pages carry the token as frappe.csrf_token; frappe-ui's fetch reads window.csrf_token.
function shareCsrfToken() {
	const page = window as unknown as { frappe?: { csrf_token?: string }; csrf_token?: string }
	page.csrf_token ||= page.frappe?.csrf_token
}

let hasToasts = false

// Apart from the island, so an inline one adds nothing to the layout around its trigger;
// toasts are module state, so any island's toast() lands here.
function mountToasts(root: HTMLElement) {
	if (hasToasts) return
	hasToasts = true
	createApp({ render: () => h(FrappeUIProvider) }).mount(
		root.appendChild(document.createElement("div")),
	)
}

function createRoot(): HTMLElement {
	const root = document.createElement("div")
	root.className = "buzz-island"
	document.body.append(root)
	return root
}

export async function openIsland(trigger: HTMLElement) {
	const existing = opened.get(trigger)
	if (existing) return void (existing.value = true)

	const loader = ISLANDS[trigger.dataset.island || ""]
	if (!loader) return
	shareCsrfToken()
	// Components call __ in <script> too, where globalProperties do not reach.
	window.__ = translate
	const component = (await loader()).default
	const open = ref(true)
	opened.set(trigger, open)

	const props = JSON.parse(trigger.dataset.props || "{}")
	const root = createRoot()
	// An inline island, such as a menu, takes the trigger's place; any other mounts at the end
	// of the page. Popups render into the root either way.
	const target = document.createElement("div")
	// Unscoped, so the page's own styles still reach what sits in the trigger's place.
	if ("islandInline" in trigger.dataset) {
		target.style.display = "contents"
		trigger.replaceWith(target)
	} else root.append(target)
	const app = createApp({
		// An island that changed the page's data reloads it.
		render: () =>
			h(component, {
				...props,
				open: open.value,
				"onUpdate:open": (value: boolean) => (open.value = value),
				onAdded: () => window.location.reload(),
			}),
	})
	app.config.globalProperties.__ = translate
	app.provide(portalTargetKey, root)
	app.mount(target)
	mountToasts(root)
}
