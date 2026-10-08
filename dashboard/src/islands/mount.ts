import { portalTargetKey } from "frappe-ui"
import { type Component, createApp, h, type Ref, ref } from "vue"

import "./islands.css"
import { translate } from "./translate"

type Loader = () => Promise<{ default: Component }>

// Each island's name, as a page's data-island names it, to its component.
const ISLANDS: Record<string, Loader> = {}

const opened = new Map<HTMLElement, Ref<boolean>>()

// Public pages carry the token as frappe.csrf_token; frappe-ui's fetch reads window.csrf_token.
function shareCsrfToken() {
	const page = window as unknown as { frappe?: { csrf_token?: string }; csrf_token?: string }
	page.csrf_token ||= page.frappe?.csrf_token
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
	const component = (await loader()).default
	const open = ref(true)
	opened.set(trigger, open)

	const props = JSON.parse(trigger.dataset.props || "{}")
	const root = createRoot()
	const app = createApp({
		render: () =>
			h(component, {
				...props,
				open: open.value,
				"onUpdate:open": (value: boolean) => (open.value = value),
			}),
	})
	app.config.globalProperties.__ = translate
	app.provide(portalTargetKey, root)
	app.mount(root.appendChild(document.createElement("div")))
}
