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

app.use(router)
app.use(translationPlugin)
app.use(resourcesPlugin)
void installTelemetry(router)

const socket = initSocket()
app.config.globalProperties.$socket = socket

for (const [key, component] of Object.entries(globalComponents)) {
	app.component(key, component)
}

app.mount("#app")
