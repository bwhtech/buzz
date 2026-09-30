import {
	Alert,
	Badge,
	Button,
	Dialog,
	ErrorMessage,
	FormControl,
	TextInput,
	frappeRequest,
	resourcesPlugin,
	setConfig,
} from "frappe-ui"
import { createApp } from "vue"

import App from "./App.vue"
import { applyLanguageFromQuery } from "./composables/useLanguage"
import router from "./router"
import { initSocket } from "./socket"
import { installTelemetry } from "./telemetry"
import translationPlugin from "./translation"

import "./index.css"

const globalComponents = {
	Button,
	TextInput,
	FormControl,
	ErrorMessage,
	Dialog,
	Alert,
	Badge,
}

const app = createApp(App)

setConfig("resourceFetcher", frappeRequest)

// Before the router runs and may redirect away from the query.
applyLanguageFromQuery(router)

// Before the router, whose afterEach translates page titles through `__`.
app.use(translationPlugin)
app.use(router)
app.use(resourcesPlugin)
installTelemetry(router).catch(() => {})

// The bench renders boot data into the page; the Vite dev server does not, so dev fetches it.
if (process.env.NODE_ENV === "development") {
	fetch("/api/method/buzz.www.dashboard.get_context_for_dev", { method: "POST" })
		.then((response) => response.json())
		.then(({ message }) => Object.assign(window, message))
		.catch(() => {})
}

const socket = initSocket()
app.config.globalProperties.$socket = socket

for (const [key, component] of Object.entries(globalComponents)) {
	app.component(key, component)
}

app.mount("#app")
